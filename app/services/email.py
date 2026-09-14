import logging
import smtplib
from email.message import EmailMessage

from ..config import get_settings


logger = logging.getLogger(__name__)


def send_password_reset_email(destination: str, reset_url: str) -> bool:
    settings = get_settings()
    if not settings.smtp_host:
        logger.warning("password_reset_email_skipped_smtp_not_configured")
        return False

    message = EmailMessage()
    message["Subject"] = "Restablece tu contraseña de JobRadar"
    message["From"] = settings.email_from
    message["To"] = destination
    message.set_content(
        "Recibimos una solicitud para restablecer tu contraseña de JobRadar.\n\n"
        f"Abre este enlace: {reset_url}\n\n"
        "El enlace caduca en 30 minutos y solo puede utilizarse una vez. "
        "Si no solicitaste el cambio, ignora este correo."
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
        return True
    except Exception:
        logger.exception("password_reset_email_failed")
        return False
