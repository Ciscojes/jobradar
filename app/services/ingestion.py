from typing import Any

from sqlalchemy.orm import Session

from .. import models
from .notifications import enqueue_offer_notification
from .persistence import get_or_create_job_offer, get_or_create_user_offer


def offer_matches_alert(offer_data: dict[str, Any], alert: models.Alert) -> bool:
    """Evalúa una oferta con las mismas reglas para ingestas manuales y periódicas."""
    if not alert.activo:
        return False

    searchable_text = " ".join(
        str(offer_data.get(field) or "")
        for field in ("titulo", "title", "descripcion", "empresa", "company")
    ).lower()
    if alert.termino.strip().lower() not in searchable_text:
        return False

    location = (alert.ubicacion or "Cualquiera").strip().lower()
    offer_location = str(
        offer_data.get("ubicacion") or offer_data.get("location") or ""
    ).lower()
    if location != "cualquiera" and location not in offer_location:
        return False

    modality = (alert.modalidad or "Cualquiera").strip().lower()
    offer_modality = str(offer_data.get("modalidad") or "").lower()
    return modality == "cualquiera" or modality in offer_modality


def build_job_offer(offer_data: dict[str, Any]) -> models.JobOffer | None:
    url_value = offer_data.get("enlace") or offer_data.get("url") or offer_data.get("id")
    if not url_value or not str(url_value).strip():
        return None

    return models.JobOffer(
        titulo=offer_data.get("titulo") or offer_data.get("title") or "Sin título",
        empresa=offer_data.get("empresa") or offer_data.get("company") or "Empresa confidencial",
        ubicacion=offer_data.get("ubicacion") or offer_data.get("location") or "No especificado",
        modalidad=offer_data.get("modalidad") or "No especificado",
        salario=offer_data.get("salario") or offer_data.get("salary") or "No especificado",
        descripcion=offer_data.get("descripcion"),
        enlace=str(url_value).strip(),
        fuente=offer_data.get("fuente") or offer_data.get("source") or "Desconocida",
        estado=offer_data.get("estado") or "guardado",
        fecha_publicacion=offer_data.get("fecha_publicacion"),
    )


def ingest_offer_for_alert(
    db: Session,
    offer_data: dict[str, Any],
    alert: models.Alert,
) -> tuple[bool, bool]:
    """Persiste oferta/match de forma idempotente y encola su notificación."""
    offer, offer_created = persist_offer(db, offer_data)
    if offer is None:
        return False, False
    match_created = match_offer_to_alert(db, offer, alert)
    return offer_created, match_created


def persist_offer(
    db: Session,
    offer_data: dict[str, Any],
) -> tuple[models.JobOffer | None, bool]:
    candidate = build_job_offer(offer_data)
    if candidate is None:
        return None, False
    return get_or_create_job_offer(db, candidate)


def match_offer_to_alert(
    db: Session,
    offer: models.JobOffer,
    alert: models.Alert,
) -> bool:
    match, match_created = get_or_create_user_offer(
        db,
        user_id=alert.user_id,
        offer_id=offer.id,
        alert_id=alert.id,
    )
    if match_created:
        enqueue_offer_notification(db, match)
    return match_created
