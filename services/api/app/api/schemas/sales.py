"""Contratos da comanda digital."""

from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models import SaleItemCategory, SalePaymentMethod, SaleStatus


class SaleItemCreateRequest(BaseModel):
    """Novo item da comanda."""

    service_id: UUID | None = None
    inventory_item_id: UUID | None = None
    category: SaleItemCategory = SaleItemCategory.SERVICE
    description: str | None = Field(default=None, max_length=255)
    quantity: int = Field(default=1, ge=1, le=100)
    unit_price: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    cost: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.service_id is None and not self.description:
            raise ValueError("Informe service_id ou description")
        if self.service_id is None and self.unit_price is None:
            raise ValueError("unit_price é obrigatório para item manual")
        return self


class SaleItemResponse(BaseModel):
    """Item retornado pela comanda."""

    id: UUID
    service_id: UUID | None
    inventory_item_id: UUID | None
    category: SaleItemCategory
    description: str
    quantity: int
    unit_price: Decimal
    cost: Decimal
    total: Decimal


class SaleResponse(BaseModel):
    """Comanda completa."""

    id: UUID
    client_id: UUID
    client_name: str
    appointment_id: UUID | None
    collaborator_id: UUID | None
    collaborator_name: str | None
    status: SaleStatus
    subtotal: Decimal
    discount: Decimal
    credit_amount: Decimal
    total: Decimal
    payment_method: SalePaymentMethod | None
    account_id: UUID | None
    financial_entry_id: UUID | None
    notes: str | None
    created_at: datetime
    closed_at: datetime | None
    items: list[SaleItemResponse]


class SaleUpdateRequest(BaseModel):
    """Desconto/observação da comanda aberta."""

    discount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    notes: str | None = Field(default=None, max_length=2000)


class SaleCloseRequest(BaseModel):
    """Fechamento da comanda."""

    payment_method: SalePaymentMethod
    account_id: UUID
    notes: str | None = Field(default=None, max_length=2000)


class SaleCreditRequest(BaseModel):
    """Aplicação de crédito do cliente na comanda."""

    credit_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class SaleAccountResponse(BaseModel):
    """Conta/caixa selecionável no fechamento."""

    id: UUID
    name: str
    type: str
