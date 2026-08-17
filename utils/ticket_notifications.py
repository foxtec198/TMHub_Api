# Utilitários de notificações de chamados.
# Biblioteca padrão.
import logging
import smtplib
from email.message import EmailMessage
from os import getenv
from threading import Thread


logger = logging.getLogger(__name__)


def _recipients(values):
    return sorted({str(value).strip().lower() for value in values if value})


def _send(recipients, subject, content):
    recipients = _recipients(recipients)
    if not recipients:
        return False

    host = getenv("SMTP_HOST")
    sender = getenv("SMTP_FROM") or getenv("SMTP_USER")
    if not host or not sender:
        raise RuntimeError("SMTP_HOST e SMTP_FROM (ou SMTP_USER) devem estar configurados.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(content)

    with smtplib.SMTP(host, int(getenv("SMTP_PORT", "587")), timeout=15) as smtp:
        if getenv("SMTP_STARTTLS", "true").strip().lower() == "true":
            smtp.starttls()
        username = getenv("SMTP_USER") or sender
        password = getenv("SMTP_PASSWORD")
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)
    return True


def notify_ticket_recipients(recipients, subject, content):
    """Email é complementar: nunca pode desfazer uma alteração já persistida."""
    recipients = _recipients(recipients)
    if not recipients:
        return

    def send():
        try:
            _send(recipients, subject, content)
        except Exception:
            logger.exception("Falha ao enviar notificação do ticket")

    Thread(target=send, name="tmhub-ticket-email", daemon=True).start()


def send_ticket_test_email(recipient):
    """Envio síncrono somente para a tela administrativa validar o SMTP."""
    return _send(
        [recipient],
        "Teste SMTP - TM Hub Tickets",
        "O SMTP do TM Hub está configurado e pronto para notificar atualizações de chamados.",
    )
