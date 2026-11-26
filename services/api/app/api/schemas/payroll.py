"""Contratos de folha de pagamento e pró-labore."""

from datetime import date, datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models import FinancialEntryStatus, PayrollKind


class PayrollEntryCreateRequest(BaseModel):
    """Nova verba de folha."""

    user_id: UUID
    kind: PayrollKind
    description: str = Field(min_length=2, max_length=2000)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    competence_date: date
    status: FinancialEntryStatus = FinancialEntryStatus.PENDING
    cash_date: date | None = None
    account_id: UUID | None = None

    @model_validator(mode="after")
    def _validate_paid(self) -> Self:
        if self.status == FinancialEntryStatus.PAID and (
            self.cash_date is None or self.account_id is None
        ):
            raise ValueError(
                "cash_date e account_id são obrigatórios para folha paga"
            )
        return self


class PayrollEntryUpdateRequest(BaseModel):
    """Atualização parcial de verba de folha."""

    kind: PayrollKind | None = None
    description: str | None = Field(default=None, min_length=2, max_length=2000)
    amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    competence_date: date | None = None
    status: FinancialEntryStatus | None = None
    cash_date: date | None = None
    account_id: UUID | None = None


class PayrollEntryResponse(BaseModel):
    """Verba de folha com o nome do usuário."""

    id: UUID
    user_id: UUID
    user_name: str
    kind: PayrollKind
    description: str
    amount: Decimal
    competence_date: date
    status: FinancialEntryStatus
    cash_date: date | None
    financial_entry_id: UUID | None
    created_at: datetime
