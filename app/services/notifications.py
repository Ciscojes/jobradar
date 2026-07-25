from collections.abc import Callable
from datetime import timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models
from .telegram import send_telegram_notification


def enqueue_offer_notification(
    db: Session,
    user_offer: models.UserOferta,
) -> models.NotificationOutbox:
    existing = (
        db.query(models.NotificationOutbox)
        .filter(models.NotificationOutbox.user_oferta_id == user_offer.id)
        .first()
    )
    if existing:
        return existing

    outbox = models.NotificationOutbox(user_oferta_id=user_offer.id)
    try:
        with db.begin_nested():
            db.add(outbox)
            db.flush()
        return outbox
    except IntegrityError:
        return (
            db.query(models.NotificationOutbox)
            .filter(models.NotificationOutbox.user_oferta_id == user_offer.id)
            .one()
        )


def process_notification_outbox(
    db: Session,
    sender: Callable[..., tuple[bool, str, str | None]] = send_telegram_notification,
    limit: int = 20,
    max_attempts: int = 5,
) -> int:
    now = models.utc_now()
    pending = (
        db.query(models.NotificationOutbox)
        .filter(
            models.NotificationOutbox.status.in_(("pending", "processing")),
            models.NotificationOutbox.available_at <= now,
        )
        .order_by(models.NotificationOutbox.id)
        .with_for_update(skip_locked=True)
        .limit(limit)
        .all()
    )
    processed = 0

    for outbox in pending:
        match = outbox.user_oferta
        offer = match.oferta
        channels = (
            db.query(models.NotificationChannel)
            .filter(
                models.NotificationChannel.user_id == match.user_id,
                models.NotificationChannel.is_active.is_(True),
                models.NotificationChannel.verified_at.is_not(None),
            )
            .all()
        )
        outbox_id = outbox.id
        match_id = match.id
        attempts = outbox.attempts + 1
        outbox.status = "processing"
        outbox.attempts = attempts
        outbox.available_at = now + timedelta(minutes=5)
        offer_data = {
            "titulo": offer.titulo,
            "empresa": offer.empresa,
            "ubicacion": offer.ubicacion,
            "modalidad": offer.modalidad,
            "salario": offer.salario,
            "fuente": offer.fuente,
            "enlace": offer.enlace,
        }
        channel_data = [
            (channel.id, channel.user_id, channel.type, channel.destination)
            for channel in channels
        ]
        db.commit()

        body = build_offer_notification_text(offer_data, markdown=True)
        results = []
        for channel_id, user_id, channel_type, destination in channel_data:
            if channel_type == "telegram":
                sent, status, error = sender(body, chat_id=destination)
            else:
                sent, status, error = False, "failed", f"Canal no soportado: {channel_type}"
            results.append((channel_id, user_id, channel_type, destination, sent, status, error))

        current = db.get(models.NotificationOutbox, outbox_id)
        current_match = db.get(models.UserOferta, match_id)
        errors = []
        sent_any = False
        for channel_id, user_id, channel_type, destination, sent, status, error in results:
            db.add(
                models.NotificationLog(
                    user_id=user_id,
                    user_oferta_id=match_id,
                    channel_id=channel_id,
                    channel_type=channel_type,
                    destination=destination,
                    status=status,
                    error_message=error,
                    sent_at=models.utc_now() if sent else None,
                )
            )
            sent_any = sent_any or sent
            if error:
                errors.append(error)

        if errors:
            current.last_error = "; ".join(errors)
            if attempts >= max_attempts:
                current.status = "failed"
            else:
                current.status = "pending"
                current.available_at = models.utc_now() + timedelta(minutes=min(2**attempts, 60))
        else:
            current.status = "sent"
            current.last_error = None
            current.processed_at = models.utc_now()
            if sent_any:
                current_match.notified_at = models.utc_now()
        db.commit()
        processed += 1

    return processed


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
    if channel.verified_at is None:
        _record_notification_log(db, channel, "failed", "Canal no verificado", user_oferta)
        return False
    if channel.type == "telegram":
        sent, status, error = send_telegram_notification(
            markdown_body or body,
            chat_id=channel.destination,
        )
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
            models.NotificationChannel.verified_at.is_not(None),
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
