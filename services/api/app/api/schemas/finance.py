"""Contratos do módulo financeiro (contas, lançamentos e dashboards)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models import (
    AccountType,
    FinancialCategory,
    FinancialEntryStatus,
    FinancialEntryType,
)

INCOME_CATEGORIES = {
    FinancialCategory.SERVICE,
    FinancialCategory.PACKAGE,
    FinancialCategory.SUBSCRIPTION,
    FinancialCategory.PRODUCT,
    FinancialCategory.OTHER_INCOME,
}
EXPENSE_CATEGORIES = set(FinancialCategory) - INCOME_CATEGORIES


class FinancialAccountCreateRequest(BaseModel):
    """Cadastro de conta/caixa."""

    name: str = Field(min_length=2, max_length=255)
    type: AccountType
    initial_balance: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )


class FinancialAccountUpdateRequest(BaseModel):
    """Atualização parcial de conta/caixa."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    is_active: bool | None = None


class FinancialAccountResponse(BaseModel):
    """Conta/caixa do tenant."""

    id: UUID
    name: str
    type: AccountType
    initial_balance: Decimal
    is_active: bool


class FinancialEntryCreateRequest(BaseModel):
    """Novo lançamento financeiro."""

    account_id: UUID
    type: FinancialEntryType
    category: FinancialCategory
    description: str = Field(min_length=2, max_length=2000)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    competence_date: date
    cash_date: date | None = None
    status: FinancialEntryStatus = FinancialEntryStatus.PENDING
    appointment_id: UUID | None = None

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.status == FinancialEntryStatus.PAID and self.cash_date is None:
            raise ValueError("cash_date é obrigatório para lançamento pago")
        if self.type == FinancialEntryType.INCOME and (
            self.category not in INCOME_CATEGORIES
        ):
            raise ValueError("categoria incompatível com entrada")
        if self.type == FinancialEntryType.EXPENSE and (
            self.category not in EXPENSE_CATEGORIES
        ):
            raise ValueError("categoria incompatível com saída")
        return self


class FinancialEntryUpdateRequest(BaseModel):
    """Atualização parcial de lançamento."""

    account_id: UUID | None = None
    category: FinancialCategory | None = None
    description: str | None = Field(default=None, min_length=2, max_length=2000)
    amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    competence_date: date | None = None
    cash_date: date | None = None
    status: FinancialEntryStatus | None = None


class FinancialEntryResponse(BaseModel):
    """Lançamento financeiro do tenant."""

    id: UUID
    account_id: UUID
    type: FinancialEntryType
    category: FinancialCategory
    description: str
    amount: Decimal
    competence_date: date
    cash_date: date | None
    status: FinancialEntryStatus
    appointment_id: UUID | None


class CashFlowResponse(BaseModel):
    """Fluxo de caixa realizado no período."""

    from_date: date
    to_date: date
    opening_balance: Decimal
    inflows: Decimal
    outflows: Decimal
    closing_balance: Decimal


class AccountBalanceResponse(BaseModel):
    """Saldo atual de uma conta/caixa."""

    account_id: UUID
    name: str
    type: AccountType
    initial_balance: Decimal
    balance: Decimal


class CommissionItemResponse(BaseModel):
    """Comissão apurada por colaborador no período."""

    collaborator_id: UUID
    collaborator_name: str
    completed_appointments: int
    gross_revenue: Decimal
    commission_amount: Decimal


class CommissionSummaryResponse(BaseModel):
    """Resumo de comissões apuradas."""

    from_date: date
    to_date: date
    items: list[CommissionItemResponse]
    total: Decimal


class DreResponse(BaseModel):
    """DRE simplificada por competência."""

    from_date: date
    to_date: date
    gross_revenue: Decimal
    deductions: Decimal
    costs: Decimal
    operating_expenses: Decimal
    net_profit: Decimal
    commissions_accrued: Decimal
    tithe_enabled: bool
    tithe_percentage: Decimal
    tithe_amount: Decimal
    offering_amount: Decimal
    after_tithe_and_offering: Decimal


class SaleItemResponse(BaseModel):
    """Valor líquido por atendimento concluído."""

    appointment_id: UUID
    starts_at: datetime
    client_name: str
    service_name: str
    collaborator_name: str
    gross_amount: Decimal
    cost_amount: Decimal
    commission_amount: Decimal
    net_amount: Decimal


class SalesResponse(BaseModel):
    """Lista de vendas/atendimentos concluídos no período."""

    from_date: date
    to_date: date
    items: list[SaleItemResponse]
    gross_total: Decimal
    net_total: Decimal


class TitheDeliveryCreateRequest(BaseModel):
    """Registro de entrega de dízimo/oferta."""

    competence_date: date
    tithe_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    offering_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _validate_total(self) -> Self:
        if self.tithe_amount + self.offering_amount <= 0:
            raise ValueError("Informe dízimo ou oferta")
        return self


class TitheDeliveryResponse(BaseModel):
    """Entrega registrada."""

    id: UUID
    competence_date: date
    tithe_amount: Decimal
    offering_amount: Decimal
    note: str | None
    created_at: datetime


class TitheSummaryResponse(BaseModel):
    """Provisão do período e histórico de entregas."""

    dre: DreResponse
    deliveries: list[TitheDeliveryResponse]
    delivered_tithe: Decimal
    delivered_offering: Decimal
    pending_tithe: Decimal
    pending_offering: Decimal
