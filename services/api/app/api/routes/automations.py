"""Endpoints de automações de relacionamento."""

from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.automations import (
    AutomationRuleResponse,
    AutomationRuleUpdateRequest,
    AutomationRunResponse,
    AutomationRunSummary,
)
from app.core.audit import client_ip, record_audit
from app.core.auth.dependencies import (
    Principal,
    get_tenant_session,
    require_roles,
)
from app.core.config import settings
from app.models import AutomationRule, AutomationRun, UserRole
from app.modules.automations.service import (
    AutomationNotFoundError,
    get_rule,
    list_rules,
    list_runs,
    run_due,
    schedule_winback_runs,
    update_rule,
)

router = APIRouter(prefix="/automations", tags=["automations"])

_require_manager = require_roles(UserRole.OWNER, UserRole.ADMIN)


def _rule_response(rule: AutomationRule) -> AutomationRuleResponse:
    return AutomationRuleResponse(
        id=rule.id,
        trigger=rule.trigger,
        name=rule.name,
        template=rule.template,
        delay_minutes=rule.delay_minutes,
        is_active=rule.is_active,
    )


def _run_response(run: AutomationRun) -> AutomationRunResponse:
    return AutomationRunResponse(
        id=run.id,
        rule_id=run.rule_id,
        client_id=run.client_id,
        appointment_id=run.appointment_id,
        status=run.status,
        scheduled_for=run.scheduled_for,
        sent_at=run.sent_at,
        error=run.error,
        created_at=run.created_at,
    )


@router.get(
    "/rules",
    response_model=list[AutomationRuleResponse],
    summary="Lista as réguas do tenant (cria os padrões se necessário)",
)
async def list_rules_endpoint(
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[AutomationRuleResponse]:
    rules = await list_rules(session, tenant_id=principal.tenant_id)
    return [_rule_response(rule) for rule in rules]


@router.patch(
    "/rules/{rule_id}",
    response_model=AutomationRuleResponse,
    summary="Atualiza template/status da régua",
)
async def update_rule_endpoint(
    rule_id: UUID,
    body: AutomationRuleUpdateRequest,
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> AutomationRuleResponse:
    try:
        rule = await get_rule(session, rule_id)
        rule = await update_rule(
            session,
            rule=rule,
            changes=body.model_dump(exclude_unset=True),
        )
    except AutomationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Régua não encontrada",
        ) from exc
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="automation.rule.update",
        resource_type="automation_rule",
        resource_id=rule.id,
        ip_address=client_ip(request),
    )
    return _rule_response(rule)


@router.get(
    "/runs",
    response_model=list[AutomationRunResponse],
    summary="Lista execuções recentes",
)
async def list_runs_endpoint(
    limit: int = Query(default=100, ge=1, le=200),
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[AutomationRunResponse]:
    runs = await list_runs(session, limit=limit)
    return [_run_response(run) for run in runs]


@router.post(
    "/run",
    response_model=AutomationRunSummary,
    summary="Executa réguas vencidas agora",
)
async def run_automations_endpoint(
    request: Request,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> AutomationRunSummary:
    today = datetime.now(
        ZoneInfo(settings.default_tenant_timezone)
    ).date()
    await schedule_winback_runs(
        session,
        tenant_id=principal.tenant_id,
        today=today,
    )
    result = await run_due(session, tenant_id=principal.tenant_id)
    audit_details: dict[str, object] = dict(result)
    await record_audit(
        session,
        tenant_id=principal.tenant_id,
        actor=principal,
        action="automation.run",
        resource_type="automation_run",
        resource_id=None,
        ip_address=client_ip(request),
        details=audit_details,
    )
    return AutomationRunSummary(**result)
