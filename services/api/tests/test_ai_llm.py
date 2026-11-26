"""Testes das validações anti-alucinação das respostas da LLM."""

import pytest
from app.modules.ai.llm import _prices, _safe_reply, _urls

pytestmark = [pytest.mark.security]


def test_extract_urls_and_brazilian_prices() -> None:
    text = "Corte R$ 120,00 e pacote R$ 1.200,50. Link: https://x.test/a"
    assert _urls(text) == {"https://x.test/a"}
    assert {str(value) for value in _prices(text)} == {"120.00", "1200.50"}


def test_safe_reply_accepts_grounded_rewrite() -> None:
    base = "O corte custa R$ 120,00. Agende em https://sora.test/public/demo"
    candidate = (
        "Nosso corte sai por R$ 120,00. "
        "Você pode escolher o horário em https://sora.test/public/demo."
    )
    assert (
        _safe_reply(intent="prices", base_reply=base, candidate=candidate)
        == candidate
    )


def test_safe_reply_rejects_invented_price_or_link() -> None:
    base = "O corte custa R$ 120,00. Agende em https://sora.test/public/demo"
    assert (
        _safe_reply(
            intent="prices",
            base_reply=base,
            candidate="O corte custa R$ 99,00.",
        )
        is None
    )
    assert (
        _safe_reply(
            intent="booking",
            base_reply=base,
            candidate="Agende em https://golpe.example",
        )
        is None
    )
    assert (
        _safe_reply(
            intent="greeting",
            base_reply="Olá!",
            candidate="Olá! Veja https://golpe.example",
        )
        is None
    )
    assert (
        _safe_reply(
            intent="fallback",
            base_reply="Posso ajudar com agendamentos.",
            candidate="O procedimento custa R$ 99,00.",
        )
        is None
    )


def test_booking_reply_must_preserve_base_link() -> None:
    base = "Agende em https://sora.test/public/demo por 20 minutos."
    assert (
        _safe_reply(
            intent="booking",
            base_reply=base,
            candidate="Claro! Escolha seu horário quando quiser.",
        )
        is None
    )
    assert (
        _safe_reply(
            intent="booking",
            base_reply=base,
            candidate="Claro! Link: https://sora.test/public/demo",
        )
        is not None
    )
