"""Porta de pagamento e provider mock (gateway real plugável)."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.core.config import settings
from app.modules.payments.pix import build_pix_payload


class PaymentProviderError(Exception):
    """Provider real ainda não configurado/implementado."""


@dataclass(frozen=True)
class PixCharge:
    """Cobrança Pix gerada pelo provider."""

    payload: str
    provider: str
    reference: str | None = None


class PaymentProviderPort(Protocol):
    """Contrato para Mock, Asaas, Mercado Pago, Stripe etc."""

    name: str

    def create_pix_charge(
        self,
        *,
        amount: Decimal,
        txid: UUID | str,
        description: str,
    ) -> PixCharge:
        """Cria a cobrança Pix e devolve copia-e-cola/QR."""


class MockPixProvider:
    """Provider local: BR Code estático, sem chamada externa."""

    name = "mock"

    def create_pix_charge(
        self,
        *,
        amount: Decimal,
        txid: UUID | str,
        description: str,
    ) -> PixCharge:
        payload = build_pix_payload(
            key=settings.payment_pix_key,
            merchant_name=settings.payment_merchant_name,
            merchant_city=settings.payment_merchant_city,
            amount=amount,
            txid=str(txid).replace("-", ""),
        )
        return PixCharge(payload=payload, provider=self.name)


class UnconfiguredPaymentProvider:
    """Falha explícita quando o gateway real ainda não foi plugado."""

    name = "unconfigured"

    def create_pix_charge(
        self,
        *,
        amount: Decimal,
        txid: UUID | str,
        description: str,
    ) -> PixCharge:
        raise PaymentProviderError(
            "Gateway de pagamento real não configurado. "
            "Use PAYMENT_PROVIDER=mock nas primeiras fases."
        )


def get_payment_provider() -> PaymentProviderPort:
    if settings.payment_provider.lower() == "mock":
        return MockPixProvider()
    return UnconfiguredPaymentProvider()
