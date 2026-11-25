"""Formatação e mascaramento de dados sensíveis."""

import re


def mask_phone(phone: str) -> str:
    """Mascara o telefone para colaboradores: (11) 9****-1234."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2]}****-{digits[-4:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) ****-{digits[-4:]}"
    return "***"
