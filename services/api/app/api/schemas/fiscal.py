"""Contratos fiscais (NFS-e)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models import FiscalInvoiceStatus


class FiscalInvoiceResponse(BaseModel):
    """Nota fiscal emitida."""

    id: UUID
    sale_id: UUID
    status: FiscalInvoiceStatus
    number: str
    provider: str
    amount: Decimal
    issued_at: datetime
    cancelled_at: datetime | None
