# Utilitários de notificações de projetos.
# Biblioteca padrão.
import logging
import smtplib
from email.message import EmailMessage
from os import getenv
from threading import Thread


logger = logging.getLogger(__name__)


def notify_card_members(recipients, subject, content):
    """Best-effort email delivery; persistence must never depend on SMTP."""
    emails = sorted({str(email).strip() for email in recipients if email})
    if not emails:
        return

    def send():
        try:
            host = getenv("SMTP_HOST")
            sender = getenv("SMTP_FROM") or getenv("SMTP_USER")
            if not host or not sender:
                raise RuntimeError("SMTP não configurado para notificações de projetos.")
            message = EmailMessage()
            message["Subject"] = subject
            message["From"] = sender
            message["To"] = ", ".join(emails)
            message.set_content(content)
            with smtplib.SMTP(host, int(getenv("SMTP_PORT", "587")), timeout=15) as smtp:
                if getenv("SMTP_STARTTLS", "true").lower() == "true":
                    smtp.starttls()
                username = getenv("SMTP_USER") or sender
                password = getenv("SMTP_PASSWORD")
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(message)
        except Exception:
            logger.exception("Falha ao enviar notificação do card")

    Thread(target=send, name="tmhub-project-email", daemon=True).start()
