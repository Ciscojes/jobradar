import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..deps import get_current_user
from ..services.scheduler import scan_single_alert

router = APIRouter(
    prefix="/alertas",
    tags=["Alertas"]
)
logger = logging.getLogger(__name__)


def get_user_alert_or_404(db: Session, alerta_id: int, user_id: int) -> models.Alerta:
    db_alerta = (
        db.query(models.Alerta)
        .filter(models.Alerta.id == alerta_id, models.Alerta.user_id == user_id)
        .first()
    )
    if not db_alerta:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return db_alerta


@router.get("/", response_model=List[schemas.Alerta])
def read_alertas(
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
        db.query(models.Alerta)
        .filter(models.Alerta.user_id == current_user.id)
        .order_by(models.Alerta.creado_en.desc(), models.Alerta.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

@router.post("/", response_model=schemas.Alerta, status_code=status.HTTP_201_CREATED)
def create_alerta(
    alerta: schemas.AlertaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_alerta = models.Alerta(**alerta.model_dump(), user_id=current_user.id)
    db.add(db_alerta)
    db.commit()
    db.refresh(db_alerta)

    # Busqueda inmediata: no esperamos al siguiente intervalo del scheduler
    # para que el usuario vea ofertas recomendadas nada mas crear la alerta.
    if db_alerta.activo:
        try:
            scan_single_alert(db, db_alerta)
        except Exception as scan_error:
            logger.exception("Alert scan failed for alert %s: %s", db_alerta.id, scan_error)

    return db_alerta


@router.get("/{alerta_id}", response_model=schemas.Alerta)
def read_alerta(
    alerta_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return get_user_alert_or_404(db, alerta_id, current_user.id)


@router.put("/{alerta_id}", response_model=schemas.Alerta)
def update_alerta(
    alerta_id: int,
    alerta: schemas.AlertaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_alerta = get_user_alert_or_404(db, alerta_id, current_user.id)
    for field, value in alerta.model_dump().items():
        setattr(db_alerta, field, value)
    db.commit()
    db.refresh(db_alerta)
    return db_alerta


@router.patch("/{alerta_id}/activar", response_model=schemas.Alerta)
def activar_alerta(
    alerta_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_alerta = get_user_alert_or_404(db, alerta_id, current_user.id)
    db_alerta.activo = True
    db.commit()
    db.refresh(db_alerta)

    try:
        scan_single_alert(db, db_alerta)
    except Exception as scan_error:
        logger.exception("Alert scan failed for alert %s: %s", db_alerta.id, scan_error)

    return db_alerta


@router.patch("/{alerta_id}/desactivar", response_model=schemas.Alerta)
def desactivar_alerta(
    alerta_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_alerta = get_user_alert_or_404(db, alerta_id, current_user.id)
    db_alerta.activo = False
    db.commit()
    db.refresh(db_alerta)
    return db_alerta


@router.delete("/{alerta_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alerta(
    alerta_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_alerta = get_user_alert_or_404(db, alerta_id, current_user.id)
    db.delete(db_alerta)
    db.commit()
    return None
