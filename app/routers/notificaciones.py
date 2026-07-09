import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..services.notifications import send_channel_notification
from ..services.telegram import get_recent_telegram_chats


router = APIRouter(
    prefix="/notificaciones",
    tags=["Notificaciones"],
)
logger = logging.getLogger(__name__)


def _normalize_channel_destination(channel_type: str, destination: str) -> str:
    normalized = destination.strip()
    if channel_type == "email":
        return normalized.lower()
    return normalized


def _channel_to_response(
    db: Session,
    channel: models.NotificationChannel,
) -> dict:
    last_log = (
        db.query(models.NotificationLog)
        .filter(models.NotificationLog.channel_id == channel.id)
        .order_by(models.NotificationLog.created_at.desc(), models.NotificationLog.id.desc())
        .first()
    )
    return {
        "id": channel.id,
        "user_id": channel.user_id,
        "type": channel.type,
        "destination": channel.destination,
        "is_active": channel.is_active,
        "verified_at": channel.verified_at,
        "created_at": channel.created_at,
        "last_notification_status": last_log.status if last_log else None,
        "last_notification_at": last_log.created_at if last_log else None,
        "last_notification_error": last_log.error_message if last_log else None,
    }


def _ensure_unique_channel(
    db: Session,
    user_id: int,
    channel_type: str,
    destination: str,
    exclude_channel_id: int | None = None,
) -> None:
    query = db.query(models.NotificationChannel).filter(
        models.NotificationChannel.user_id == user_id,
        models.NotificationChannel.type == channel_type,
        models.NotificationChannel.destination == destination,
    )
    if exclude_channel_id is not None:
        query = query.filter(models.NotificationChannel.id != exclude_channel_id)
    if query.first():
        raise HTTPException(status_code=400, detail="Ya tienes un aviso configurado con ese destino")


@router.get("/canales", response_model=List[schemas.NotificationChannel])
def read_channels(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 100")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset debe ser mayor o igual que 0")

    channels = (
        db.query(models.NotificationChannel)
        .filter(models.NotificationChannel.user_id == current_user.id)
        .order_by(models.NotificationChannel.created_at.desc(), models.NotificationChannel.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_channel_to_response(db, channel) for channel in channels]


@router.post(
    "/canales",
    response_model=schemas.NotificationChannel,
    status_code=status.HTTP_201_CREATED,
)
def create_channel(
    payload: schemas.NotificationChannelCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    channel_type = payload.type.lower().strip()
    if channel_type not in {"telegram", "email"}:
        raise HTTPException(status_code=400, detail="El canal debe ser 'telegram' o 'email'")
    destination = _normalize_channel_destination(channel_type, payload.destination)
    if not destination:
        raise HTTPException(status_code=400, detail="El destino del aviso es obligatorio")
    _ensure_unique_channel(db, current_user.id, channel_type, destination)

    channel = models.NotificationChannel(
        user_id=current_user.id,
        type=channel_type,
        destination=destination,
        is_active=payload.is_active,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)

    # Mensaje de bienvenida automatico: en cuanto el usuario conecta un canal,
    # le llega confirmacion de que JobRadar ya puede notificarle por ahi.
    if channel.is_active:
        nombre = current_user.nombre or current_user.email
        try:
            send_channel_notification(
                db,
                channel,
                subject="¡Bienvenido a JobRadar!",
                body=(
                    f"Hola {nombre}, tu canal de {channel.type} ya está conectado. "
                    "A partir de ahora recibirás aquí las ofertas que coincidan con tus alertas."
                ),
                markdown_body=(
                    f"*¡Bienvenido a JobRadar, {nombre}!*\n\n"
                    f"Tu canal de *{channel.type}* ya está conectado. "
                    "A partir de ahora recibirás aquí las ofertas que coincidan con tus alertas."
                ),
            )
            db.commit()
        except Exception as welcome_error:
            logger.exception("Welcome notification failed for channel %s: %s", channel.id, welcome_error)

    return channel


@router.get("/telegram/chats")
def read_recent_telegram_chats(
    current_user: models.User = Depends(get_current_user),
):
    chats, error = get_recent_telegram_chats()
    if error:
        raise HTTPException(status_code=502, detail=error)
    return {"chats": chats, "user_id": current_user.id}


@router.patch("/canales/{channel_id}", response_model=schemas.NotificationChannel)
def update_channel(
    channel_id: int,
    payload: schemas.NotificationChannelUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    channel = (
        db.query(models.NotificationChannel)
        .filter(
            models.NotificationChannel.id == channel_id,
            models.NotificationChannel.user_id == current_user.id,
        )
        .first()
    )
    if not channel:
        raise HTTPException(status_code=404, detail="Canal no encontrado")

    updates = payload.model_dump(exclude_unset=True)
    new_type = updates.get("type", channel.type)
    if isinstance(new_type, str):
        new_type = new_type.lower().strip()
    if new_type not in {"telegram", "email"}:
        raise HTTPException(status_code=400, detail="El canal debe ser 'telegram' o 'email'")

    new_destination = updates.get("destination", channel.destination)
    if isinstance(new_destination, str):
        new_destination = _normalize_channel_destination(new_type, new_destination)
    if not new_destination:
        raise HTTPException(status_code=400, detail="El destino del aviso es obligatorio")

    _ensure_unique_channel(
        db,
        current_user.id,
        new_type,
        new_destination,
        exclude_channel_id=channel.id,
    )

    for field, value in updates.items():
        if field == "type":
            value = new_type
        elif field == "destination":
            value = new_destination
        setattr(channel, field, value)

    db.commit()
    db.refresh(channel)
    return channel


@router.post("/canales/{channel_id}/test")
def test_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    channel = (
        db.query(models.NotificationChannel)
        .filter(
            models.NotificationChannel.id == channel_id,
            models.NotificationChannel.user_id == current_user.id,
        )
        .first()
    )
    if not channel:
        raise HTTPException(status_code=404, detail="Canal no encontrado")
    if not channel.is_active:
        raise HTTPException(status_code=400, detail="El canal está inactivo")

    sent = send_channel_notification(
        db,
        channel,
        subject="Prueba de notificación de JobRadar",
        body="Este es un mensaje de prueba de JobRadar.",
        markdown_body="Prueba de notificación de JobRadar.",
    )
    db.commit()
    if not sent:
        raise HTTPException(status_code=502, detail="No se pudo enviar la prueba")
    return {"status": "sent"}


@router.get("/logs", response_model=List[schemas.NotificationLog])
def read_notification_logs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 100")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset debe ser mayor o igual que 0")

    return (
        db.query(models.NotificationLog)
        .filter(models.NotificationLog.user_id == current_user.id)
        .order_by(models.NotificationLog.created_at.desc(), models.NotificationLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.delete("/canales/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    channel = (
        db.query(models.NotificationChannel)
        .filter(
            models.NotificationChannel.id == channel_id,
            models.NotificationChannel.user_id == current_user.id,
        )
        .first()
    )
    if not channel:
        raise HTTPException(status_code=404, detail="Canal no encontrado")
    db.delete(channel)
    db.commit()
    return None
