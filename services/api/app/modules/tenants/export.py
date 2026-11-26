"""Exportação completa dos dados do tenant (portabilidade LGPD)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_text
from app.models import (
    Appointment,
    Client,
    ClientCredit,
    ClientSubscription,
    FinancialAccount,
    FinancialEntry,
    LgpdConsent,
    MedicalRecord,
    Package,
    Service,
    SubscriptionPlan,
    Tenant,
    User,
)


def _value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return value


async def export_tenant_data(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> dict[str, Any]:
    """Monta um JSON portável com os principais dados da clínica."""
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant inexistente")

    users = (
        await session.scalars(select(User).order_by(User.full_name))
    ).all()
    clients = (
        await session.scalars(select(Client).order_by(Client.full_name))
    ).all()
    services = (
        await session.scalars(select(Service).order_by(Service.name))
    ).all()
    packages = (
        await session.scalars(select(Package).order_by(Package.name))
    ).all()
    plans = (
        await session.scalars(
            select(SubscriptionPlan).order_by(SubscriptionPlan.name)
        )
    ).all()
    subscriptions = (
        await session.scalars(
            select(ClientSubscription).order_by(
                ClientSubscription.created_at.desc()
            )
        )
    ).all()
    appointments = (
        await session.scalars(
            select(Appointment).order_by(Appointment.starts_at.desc())
        )
    ).all()
    accounts = (
        await session.scalars(
            select(FinancialAccount).order_by(FinancialAccount.name)
        )
    ).all()
    entries = (
        await session.scalars(
            select(FinancialEntry).order_by(
                FinancialEntry.competence_date.desc()
            )
        )
    ).all()
    credits = (
        await session.scalars(
            select(ClientCredit).order_by(ClientCredit.created_at.desc())
        )
    ).all()
    records = (
        await session.scalars(
            select(MedicalRecord).order_by(MedicalRecord.created_at.desc())
        )
    ).all()
    consents = (
        await session.scalars(
            select(LgpdConsent).order_by(LgpdConsent.accepted_at.desc())
        )
    ).all()

    return {
        "exported_at": datetime.now().isoformat(),
        "tenant": {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "tax_regime": tenant.tax_regime.value,
            "is_active": tenant.is_active,
            "created_at": _value(tenant.created_at),
        },
        "users": [
            {
                "id": str(user.id),
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role.value,
                "is_active": user.is_active,
                "commission_percentage": _value(user.commission_percentage),
                "commission_fixed": _value(user.commission_fixed),
                "commission_base": user.commission_base.value,
            }
            for user in users
        ],
        "clients": [
            {
                "id": str(client.id),
                "full_name": client.full_name,
                "phone": client.phone,
                "email": client.email,
                "birth_date": _value(client.birth_date),
                "address_zip": client.address_zip,
                "address_street": client.address_street,
                "address_number": client.address_number,
                "address_complement": client.address_complement,
                "address_neighborhood": client.address_neighborhood,
                "address_city": client.address_city,
                "address_state": client.address_state,
                "notes": (
                    decrypt_text(client.notes_encrypted)
                    if client.notes_encrypted
                    else None
                ),
                "score": client.score,
                "is_blocked": client.is_blocked,
                "created_at": _value(client.created_at),
            }
            for client in clients
        ],
        "services": [
            {
                "id": str(service.id),
                "name": service.name,
                "description": service.description,
                "duration_minutes": service.duration_minutes,
                "buffer_minutes": service.buffer_minutes,
                "price": _value(service.price),
                "cost": _value(service.cost),
                "requires_deposit": service.requires_deposit,
                "deposit_amount": _value(service.deposit_amount),
                "show_average_price": service.show_average_price,
                "is_active": service.is_active,
            }
            for service in services
        ],
        "packages": [
            {
                "id": str(package.id),
                "name": package.name,
                "description": package.description,
                "total_price": _value(package.total_price),
                "is_active": package.is_active,
                "items": [
                    {
                        "service_id": str(item.service_id),
                        "quantity": item.quantity,
                    }
                    for item in package.items
                ],
            }
            for package in packages
        ],
        "subscription_plans": [
            {
                "id": str(plan.id),
                "name": plan.name,
                "description": plan.description,
                "price": _value(plan.price),
                "billing_cycle": plan.billing_cycle.value,
                "is_active": plan.is_active,
                "items": [
                    {
                        "service_id": str(item.service_id),
                        "uses_per_cycle": item.uses_per_cycle,
                        "min_interval_days": item.min_interval_days,
                        "allowed_weekdays": item.allowed_weekdays,
                    }
                    for item in plan.items
                ],
            }
            for plan in plans
        ],
        "client_subscriptions": [
            {
                "id": str(subscription.id),
                "client_name": subscription.client.full_name,
                "plan_name": subscription.plan.name,
                "status": subscription.status.value,
                "started_at": _value(subscription.started_at),
                "current_period_start": _value(
                    subscription.current_period_start
                ),
                "current_period_end": _value(subscription.current_period_end),
            }
            for subscription in subscriptions
        ],
        "appointments": [
            {
                "id": str(appointment.id),
                "client_name": appointment.client.full_name,
                "service_name": appointment.service.name,
                "collaborator_name": appointment.collaborator.full_name,
                "starts_at": _value(appointment.starts_at),
                "ends_at": _value(appointment.ends_at),
                "status": appointment.status.value,
                "deposit_amount": _value(appointment.deposit_amount),
                "subscription_id": _value(appointment.subscription_id),
            }
            for appointment in appointments
        ],
        "financial_accounts": [
            {
                "id": str(account.id),
                "name": account.name,
                "type": account.type.value,
                "initial_balance": _value(account.initial_balance),
                "is_active": account.is_active,
            }
            for account in accounts
        ],
        "financial_entries": [
            {
                "id": str(entry.id),
                "account_id": str(entry.account_id),
                "type": entry.type.value,
                "category": entry.category.value,
                "description": entry.description,
                "amount": _value(entry.amount),
                "competence_date": _value(entry.competence_date),
                "cash_date": _value(entry.cash_date),
                "status": entry.status.value,
            }
            for entry in entries
        ],
        "client_credits": [
            {
                "id": str(credit.id),
                "client_name": credit.client.full_name,
                "amount": _value(credit.amount),
                "used_amount": _value(credit.used_amount),
                "reason": credit.reason,
                "reference": credit.reference,
                "expires_at": _value(credit.expires_at),
            }
            for credit in credits
        ],
        "medical_records": [
            {
                "id": str(record.id),
                "client_name": record.client.full_name,
                "title": record.title,
                "notes": decrypt_text(record.notes_encrypted),
                "created_at": _value(record.created_at),
                "attachments": [
                    {
                        "id": str(attachment.id),
                        "filename": attachment.filename,
                        "content_type": attachment.content_type,
                        "size_bytes": attachment.size_bytes,
                        "created_at": _value(attachment.created_at),
                    }
                    for attachment in record.attachments
                ],
            }
            for record in records
        ],
        "lgpd_consents": [
            {
                "id": str(consent.id),
                "client_id": str(consent.client_id),
                "accepted_at": _value(consent.accepted_at),
                "terms_version": consent.terms_version,
                "purposes": consent.purposes,
            }
            for consent in consents
        ],
    }
