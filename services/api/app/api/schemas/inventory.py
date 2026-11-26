"""Contratos de estoque de insumos."""

from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models import StockMovementType


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
    """Entrada, saída ou ajuste de saldo."""

    kind: StockMovementType
    quantity: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_kind(self) -> Self:
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
    created_at: datetime
