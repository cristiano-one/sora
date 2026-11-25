"""Contratos de serviços, pacotes e planos de assinatura."""

from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models import BillingCycle


class ServiceCreateRequest(BaseModel):
    """Cadastro de serviço do catálogo."""

    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    duration_minutes: int = Field(ge=5, le=1440)
    buffer_minutes: int = Field(default=0, ge=0, le=240)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    cost: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    requires_deposit: bool = False
    deposit_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    show_average_price: bool = True
    is_active: bool = True

    @model_validator(mode="after")
    def _validate_deposit(self) -> Self:
        if self.requires_deposit and (
            self.deposit_amount is None or self.deposit_amount <= 0
        ):
            raise ValueError(
                "deposit_amount é obrigatório e positivo quando "
                "requires_deposit=true"
            )
        return self


class ServiceUpdateRequest(BaseModel):
    """Atualização parcial de serviço."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    duration_minutes: int | None = Field(default=None, ge=5, le=1440)
    buffer_minutes: int | None = Field(default=None, ge=0, le=240)
    price: Decimal | None = Field(
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
    requires_deposit: bool | None = None
    deposit_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    show_average_price: bool | None = None
    is_active: bool | None = None


class ServiceResponse(BaseModel):
    """Dados públicos de um serviço."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    duration_minutes: int
    buffer_minutes: int
    price: Decimal
    cost: Decimal
    requires_deposit: bool
    deposit_amount: Decimal | None
    show_average_price: bool
    is_active: bool


class PackageItemInput(BaseModel):
    """Serviço e quantidade incluídos em um pacote."""

    service_id: UUID
    quantity: int = Field(ge=1, le=100)


class PackageCreateRequest(BaseModel):
    """Cadastro de pacote de serviços."""

    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    total_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    items: list[PackageItemInput] = Field(min_length=1, max_length=50)
    is_active: bool = True

    @model_validator(mode="after")
    def _validate_unique_services(self) -> Self:
        service_ids = [item.service_id for item in self.items]
        if len(service_ids) != len(set(service_ids)):
            raise ValueError("Cada serviço pode aparecer apenas uma vez no pacote")
        return self


class PackageUpdateRequest(BaseModel):
    """Atualização parcial de pacote."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    total_price: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    is_active: bool | None = None


class PackageItemResponse(BaseModel):
    """Item de um pacote."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    quantity: int


class PackageResponse(BaseModel):
    """Dados públicos de um pacote."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    total_price: Decimal
    is_active: bool
    items: list[PackageItemResponse]


class SubscriptionPlanItemInput(BaseModel):
    """Cota de serviço incluída em um plano."""

    service_id: UUID
    uses_per_cycle: int = Field(ge=1, le=100)
    min_interval_days: int | None = Field(default=None, ge=0, le=365)
    allowed_weekdays: list[int] | None = None

    @field_validator("allowed_weekdays")
    @classmethod
    def _validate_weekdays(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("allowed_weekdays deve conter valores entre 0 e 6")
        return sorted(set(value))


class SubscriptionPlanCreateRequest(BaseModel):
    """Cadastro de plano de assinatura."""

    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    billing_cycle: BillingCycle
    items: list[SubscriptionPlanItemInput] = Field(min_length=1, max_length=50)
    is_active: bool = True

    @model_validator(mode="after")
    def _validate_unique_services(self) -> Self:
        service_ids = [item.service_id for item in self.items]
        if len(service_ids) != len(set(service_ids)):
            raise ValueError("Cada serviço pode aparecer apenas uma vez no plano")
        return self


class SubscriptionPlanUpdateRequest(BaseModel):
    """Atualização parcial de plano de assinatura."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    billing_cycle: BillingCycle | None = None
    is_active: bool | None = None


class SubscriptionPlanItemResponse(BaseModel):
    """Item de um plano de assinatura."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    uses_per_cycle: int
    min_interval_days: int | None
    allowed_weekdays: list[int] | None


class SubscriptionPlanResponse(BaseModel):
    """Dados públicos de um plano de assinatura."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    price: Decimal
    billing_cycle: BillingCycle
    is_active: bool
    items: list[SubscriptionPlanItemResponse]
