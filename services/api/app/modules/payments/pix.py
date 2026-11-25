"""Geração de payload Pix Copia e Cola (BR Code) para o provider mock."""

import re
import unicodedata
from decimal import Decimal


def _emv(field_id: str, value: str) -> str:
    return f"{field_id}{len(value):02d}{value}"


def _sanitize(value: str, max_length: int) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9 ]", "", ascii_value).strip().upper()
    return cleaned[:max_length]


def crc16_ccitt(payload: str) -> str:
    """CRC16/CCITT-FALSE exigido pelo BR Code."""
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = (
                ((crc << 1) ^ 0x1021) & 0xFFFF
                if crc & 0x8000
                else (crc << 1) & 0xFFFF
            )
    return f"{crc:04X}"


def build_pix_payload(
    *,
    key: str,
    merchant_name: str,
    merchant_city: str,
    amount: Decimal,
    txid: str,
) -> str:
    """Monta um BR Code estático com valor e txid."""
    name = _sanitize(merchant_name, 25) or "SORA STUDIO"
    city = _sanitize(merchant_city, 15) or "SAO PAULO"
    reference = re.sub(r"[^A-Za-z0-9]", "", txid)[:25] or "***"
    merchant_account = _emv("00", "BR.GOV.BCB.PIX") + _emv("01", key)
    payload = "".join(
        (
            _emv("00", "01"),
            _emv("26", merchant_account),
            _emv("52", "0000"),
            _emv("53", "986"),
            _emv("54", f"{amount:.2f}"),
            _emv("58", "BR"),
            _emv("59", name),
            _emv("60", city),
            _emv("62", _emv("05", reference)),
            "6304",
        )
    )
    return payload + crc16_ccitt(payload)
