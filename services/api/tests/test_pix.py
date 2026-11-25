"""Testes do BR Code Pix mock e do QR."""

from decimal import Decimal

from app.modules.payments.pix import build_pix_payload, crc16_ccitt
from app.modules.payments.service import qr_code_data_uri


def test_crc16_known_vector() -> None:
    assert crc16_ccitt("123456789") == "29B1"


def test_pix_payload_has_valid_crc_and_amount() -> None:
    payload = build_pix_payload(
        key="pix@sora.local",
        merchant_name="Sora Studio",
        merchant_city="São Paulo",
        amount=Decimal("50.00"),
        txid="abc-123",
    )

    assert payload.startswith("000201")
    assert "BR.GOV.BCB.PIX" in payload
    assert "540550.00" in payload
    assert payload.endswith(crc16_ccitt(payload[:-4]))
    assert "SORA STUDIO" in payload
    assert "SAO PAULO" in payload
    assert "abc123" in payload


def test_qr_data_uri_is_png() -> None:
    uri = qr_code_data_uri("000201mock")

    assert uri.startswith("data:image/png;base64,")
    assert len(uri) > 100
