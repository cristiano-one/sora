"""Normalização de payloads do webhook oficial da Meta (Cloud API)."""

import re
from dataclasses import dataclass
from typing import cast

from app.modules.agenda.public_service import PublicBookingError, normalize_phone


@dataclass(frozen=True)
class MetaInboundMessage:
    """Mensagem de texto pronta para a engine da SORA IA."""

    phone_number_id: str
    phone: str
    text: str
    external_id: str | None


def _as_dict(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return None


def _as_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _as_text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _message_text(message: dict[str, object]) -> str | None:
    message_type = _as_text(message.get("type"))
    if message_type == "text":
        text = _as_dict(message.get("text"))
        return _as_text(text.get("body")) if text is not None else None
    if message_type == "button":
        button = _as_dict(message.get("button"))
        return _as_text(button.get("text")) if button is not None else None
    if message_type == "interactive":
        interactive = _as_dict(message.get("interactive"))
        if interactive is None:
            return None
        for key in ("button_reply", "list_reply"):
            reply = _as_dict(interactive.get(key))
            if reply is not None:
                title = _as_text(reply.get("title"))
                if title:
                    return title
    return None


def parse_inbound_messages(payload: object) -> list[MetaInboundMessage]:
    """Extrai somente mensagens de texto; ignora status e eventos desconhecidos."""
    root = _as_dict(payload)
    if root is None:
        return []
    result: list[MetaInboundMessage] = []
    for entry_value in _as_list(root.get("entry")):
        entry = _as_dict(entry_value)
        if entry is None:
            continue
        for change_value in _as_list(entry.get("changes")):
            change = _as_dict(change_value)
            if change is None or change.get("field") != "messages":
                continue
            value = _as_dict(change.get("value"))
            if value is None:
                continue
            metadata = _as_dict(value.get("metadata"))
            if metadata is None:
                continue
            phone_number_id = _as_text(metadata.get("phone_number_id"))
            if phone_number_id is None:
                continue
            for message_value in _as_list(value.get("messages")):
                message = _as_dict(message_value)
                if message is None:
                    continue
                text = _message_text(message)
                phone = _as_text(message.get("from"))
                if text is None or phone is None:
                    continue
                digits = re.sub(r"\D", "", phone)
                if not digits:
                    continue
                try:
                    normalized = normalize_phone(digits)
                except PublicBookingError:
                    continue
                result.append(
                    MetaInboundMessage(
                        phone_number_id=phone_number_id,
                        phone=normalized,
                        text=text,
                        external_id=_as_text(message.get("id")),
                    )
                )
    return result
