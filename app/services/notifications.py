from typing import Any

from sqlalchemy.orm import Session

from .. import models
from .email import send_email_notification
from .telegram import send_telegram_notification


def build_offer_notification_text(offer_data: dict[str, Any], markdown: bool = False) -> str:
    if markdown:
        return (
            f"*Nueva oferta encontrada*\n\n"
            f"*Puesto:* {offer_data.get('titulo')}\n"
            f"*Empresa:* {offer_data.get('empresa')}\n"
            f"*Ubicacion:* {offer_data.get('ubicacion')}\n"
            f"*Modalidad:* {offer_data.get('modalidad')}\n"
            f"*Salario:* {offer_data.get('salario')}\n"
            f"*Fuente:* {offer_data.get('fuente')}\n\n"
            f"[Ver oferta]({offer_data.get('enlace')})"
        )

    return (
        "Nueva oferta encontrada\n\n"
        f"Puesto: {offer_data.get('titulo')}\n"
        f"Empresa: {offer_data.get('empresa')}\n"
        f"Ubicacion: {offer_data.get('ubicacion')}\n"
        f"Modalidad: {offer_data.get('modalidad')}\n"
        f"Salario: {offer_data.get('salario')}\n"
        f"Fuente: {offer_data.get('fuente')}\n\n"
        f"Ver oferta: {offer_data.get('enlace')}"
    )


def _record_notification_log(
    db: Session,
    channel: models.NotificationChannel,
    status: str,
    error_message: str | None = None,
    user_oferta: models.UserOferta | None = None,
) -> models.NotificationLog:
    sent_at = models.utc_now() if status in {"sent", "simulated"} else None
    log = models.NotificationLog(
        user_id=channel.user_id,
        user_oferta_id=user_oferta.id if user_oferta else None,
        channel_id=channel.id,
        channel_type=channel.type,
        destination=channel.destination,
        status=status,
        error_message=error_message,
        sent_at=sent_at,
    )
    db.add(log)
    return log


def send_channel_notification(
    db: Session,
    channel: models.NotificationChannel,
    subject: str,
    body: str,
    markdown_body: str | None = None,
    user_oferta: models.UserOferta | None = None,
) -> bool:
    if channel.type == "telegram":
        sent, status, error = send_telegram_notification(
            markdown_body or body,
            chat_id=channel.destination,
        )
    elif channel.type == "email":
        sent, status, error = send_email_notification(channel.destination, subject, body)
    else:
        sent, status, error = False, "failed", f"Canal no soportado: {channel.type}"

    _record_notification_log(db, channel, status, error, user_oferta)
    if sent and user_oferta:
        user_oferta.notified_at = models.utc_now()
    return sent


def notify_user_offer(db: Session, user_offer: models.UserOferta, offer_data: dict[str, Any]) -> int:
    channels = (
        db.query(models.NotificationChannel)
        .filter(
            models.NotificationChannel.user_id == user_offer.user_id,
            models.NotificationChannel.is_active.is_(True),
        )
        .all()
    )
    sent_count = 0
    subject = f"Nueva oferta: {offer_data.get('titulo', 'Oferta encontrada')}"
    body = build_offer_notification_text(offer_data)
    markdown_body = build_offer_notification_text(offer_data, markdown=True)

    for channel in channels:
        if send_channel_notification(db, channel, subject, body, markdown_body, user_offer):
            sent_count += 1

    return sent_count
