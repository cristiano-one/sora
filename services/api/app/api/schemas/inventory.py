"""Contratos de estoque de insumos."""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models import (
    StockDocumentType,
    StockMovementType,
    StockPaymentMethod,
)


class InventoryItemCreateRequest(BaseModel):
    """Cadastro de insumo."""

    name: str = Field(min_length=2, max_length=255)
    unit: str = Field(default="un", min_length=1, max_length=20)
    quantity: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=12,
        decimal_places=3,
    )
    min_quantity: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=12,
        decimal_places=3,
    )
    unit_cost: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    is_active: bool = True


class InventoryItemUpdateRequest(BaseModel):
    """Atualização parcial de insumo (sem alterar saldo)."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    min_quantity: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=3,
    )
    unit_cost: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    is_active: bool | None = None


class StockMovementCreateRequest(BaseModel):
    """Entrada, saída ou ajuste de saldo.

    Em entradas de compra, os campos de documento permitem registrar os dados
    básicos da nota fiscal, recibo ou cupom.
    """

    kind: StockMovementType
    quantity: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    reason: str | None = Field(default=None, max_length=500)
    document_type: StockDocumentType | None = None
    document_number: str | None = Field(default=None, max_length=60)
    document_series: str | None = Field(default=None, max_length=20)
    supplier_name: str | None = Field(default=None, max_length=255)
    supplier_tax_id: str | None = Field(default=None, max_length=20)
    issue_date: date | None = None
    total_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    payment_method: StockPaymentMethod | None = None
    access_key: str | None = Field(default=None, max_length=44)

    @field_validator("access_key")
    @classmethod
    def _validate_access_key(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        digits = re.sub(r"\D", "", value)
        if len(digits) != 44:
            raise ValueError("access_key deve ter 44 dígitos")
        return digits

    @model_validator(mode="after")
    def _validate_kind(self) -> Self:
        document_fields = (
            "document_type",
            "document_number",
            "document_series",
            "supplier_name",
            "supplier_tax_id",
            "issue_date",
            "total_amount",
            "payment_method",
            "access_key",
        )
        has_document = any(getattr(self, field) is not None for field in document_fields)
        if has_document and self.kind != StockMovementType.IN:
            raise ValueError("Dados de nota/recibo só podem ser informados em entradas")
        if self.kind == StockMovementType.ADJUSTMENT:
            return self
        if self.quantity <= 0:
            raise ValueError("quantity deve ser positivo")
        return self


class InventoryItemResponse(BaseModel):
    """Insumo com saldo atual e alerta de mínimo."""

    id: UUID
    name: str
    unit: str
    quantity: Decimal
    min_quantity: Decimal
    unit_cost: Decimal
    is_active: bool
    low_stock: bool
    total_value: Decimal
    created_at: datetime


class StockMovementResponse(BaseModel):
    """Movimentação registrada."""

    id: UUID
    item_id: UUID
    kind: StockMovementType
    quantity: Decimal
    reason: str | None
    document_type: StockDocumentType | None
    document_number: str | None
    document_series: str | None
    supplier_name: str | None
    supplier_tax_id: str | None
    issue_date: date | None
    total_amount: Decimal | None
    payment_method: StockPaymentMethod | None
    access_key: str | None
    created_at: datetime
