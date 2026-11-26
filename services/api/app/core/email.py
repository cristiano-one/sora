"""Envio de e-mail transacional (mock em dev, SMTP em produção)."""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(*, to: str, subject: str, body: str) -> bool:
    """Envia e-mail; em modo mock apenas registra o conteúdo no log."""
    if settings.email_provider != "smtp" or not settings.smtp_host:
        logger.info("email mock to=%s subject=%s body=%s", to, subject, body)
        return False

    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        logger.exception("falha ao enviar e-mail para %s", to)
        return False
