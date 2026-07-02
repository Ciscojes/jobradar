from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..services.notifications import send_channel_notification


router = APIRouter(
    prefix="/notificaciones",
    tags=["Notificaciones"],
)


@router.get("/canales", response_model=List[schemas.NotificationChannel])
def read_channels(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.NotificationChannel)
        .filter(models.NotificationChannel.user_id == current_user.id)
        .all()
    )


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
    channel_type = payload.type.lower()
    if channel_type not in {"telegram", "email"}:
        raise HTTPException(status_code=400, detail="El canal debe ser 'telegram' o 'email'")

    channel = models.NotificationChannel(
        user_id=current_user.id,
        type=channel_type,
        destination=payload.destination,
        is_active=payload.is_active,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


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

    for field, value in payload.model_dump(exclude_unset=True).items():
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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.NotificationLog)
        .filter(models.NotificationLog.user_id == current_user.id)
        .order_by(models.NotificationLog.created_at.desc())
        .limit(100)
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
