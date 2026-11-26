"""Adapter fiscal mock para NFS-e (pronto para provedor real)."""

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.rls import set_tenant_context
from app.models import (
    FiscalInvoice,
    FiscalInvoiceStatus,
    Sale,
    SaleStatus,
    TenantSettings,
)


class FiscalNotFoundError(Exception):
    """Nota fiscal inexistente."""


class FiscalValidationError(Exception):
    """Emissão fiscal inválida."""


async def get_invoice(
    session: AsyncSession,
    *,
    sale_id: UUID,
) -> FiscalInvoice | None:
    return await session.scalar(
        select(FiscalInvoice).where(FiscalInvoice.sale_id == sale_id)
    )


async def issue_invoice(
    session: AsyncSession,
    *,
    sale: Sale,
) -> FiscalInvoice:
    if sale.status != SaleStatus.PAID:
        raise FiscalValidationError("A comanda precisa estar paga")
    settings = await session.get(TenantSettings, sale.tenant_id)
    if settings is None or not settings.fiscal_enabled:
        raise FiscalValidationError("NFS-e não está habilitada")
    existing = await get_invoice(session, sale_id=sale.id)
    if existing is not None:
        if existing.status == FiscalInvoiceStatus.ISSUED:
            return existing
        raise FiscalValidationError("Já existe nota cancelada para a comanda")

    invoice = FiscalInvoice(
        id=uuid4(),
        tenant_id=sale.tenant_id,
        sale_id=sale.id,
        status=FiscalInvoiceStatus.ISSUED,
        number=f"MOCK-{sale.id.hex[:10].upper()}",
        provider=settings.fiscal_provider or "mock",
        amount=sale.total,
        payload=json.dumps(
            {
                "sale_id": str(sale.id),
                "client": sale.client.full_name,
                "items": [
                    {
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                    }
                    for item in sale.items
                ],
                "total": str(sale.total),
                "municipality": settings.fiscal_municipality,
                "service_code": settings.fiscal_service_code,
                "email": settings.fiscal_email,
            },
            ensure_ascii=False,
        ),
        issued_at=datetime.now(UTC),
    )
    session.add(invoice)
    await session.commit()
    await set_tenant_context(session, sale.tenant_id)
    return invoice


async def cancel_invoice(
    session: AsyncSession,
    *,
    invoice: FiscalInvoice,
) -> FiscalInvoice:
    if invoice.status != FiscalInvoiceStatus.ISSUED:
        raise FiscalValidationError("Nota não está emitida")
    invoice.status = FiscalInvoiceStatus.CANCELLED
    invoice.cancelled_at = datetime.now(UTC)
    await session.commit()
    await set_tenant_context(session, invoice.tenant_id)
    return invoice
