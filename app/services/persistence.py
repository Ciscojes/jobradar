from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models


def get_or_create_job_offer(
    db: Session,
    candidate: models.JobOffer,
) -> tuple[models.JobOffer, bool]:
    existing = (
        db.query(models.JobOffer)
        .filter(models.JobOffer.enlace == candidate.enlace)
        .first()
    )
    if existing:
        return existing, False

    try:
        with db.begin_nested():
            db.add(candidate)
            db.flush()
        return candidate, True
    except IntegrityError:
        existing = (
            db.query(models.JobOffer)
            .filter(models.JobOffer.enlace == candidate.enlace)
            .one()
        )
        return existing, False


def get_or_create_user_offer(
    db: Session,
    user_id: int,
    offer_id: int,
    alert_id: int | None,
) -> tuple[models.UserOferta, bool]:
    existing = (
        db.query(models.UserOferta)
        .filter(
            models.UserOferta.user_id == user_id,
            models.UserOferta.oferta_id == offer_id,
        )
        .first()
    )
    if existing:
        return existing, False

    candidate = models.UserOferta(
        user_id=user_id,
        oferta_id=offer_id,
        alerta_id=alert_id,
        estado="guardado",
        matched_at=models.utc_now(),
    )
    try:
        with db.begin_nested():
            db.add(candidate)
            db.flush()
        return candidate, True
    except IntegrityError:
        existing = (
            db.query(models.UserOferta)
            .filter(
                models.UserOferta.user_id == user_id,
                models.UserOferta.oferta_id == offer_id,
            )
            .one()
        )
        return existing, False
