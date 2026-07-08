import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_email_notification(to_email: str, subject: str, body: str) -> tuple[bool, str, str | None]:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_from = os.getenv("EMAIL_FROM") or smtp_user

    if not smtp_host or not smtp_user or not smtp_password or not email_from:
        logger.info("Email notification simulated for %s with subject %s", to_email, subject)
        return True, "simulated", None

    message = EmailMessage()
    message["From"] = email_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
        return True, "sent", None
    except Exception as exc:
        return False, "failed", str(exc)
