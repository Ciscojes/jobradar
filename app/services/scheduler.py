import logging
import os
from collections.abc import Callable
from datetime import datetime
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import STATE_PAUSED, STATE_RUNNING, STATE_STOPPED
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .. import models
from ..database import SessionLocal
from ..scraper.adzuna import search_adzuna_offers
from .notifications import notify_user_offer


SCHEDULER_JOB_ID = "jobradar_adzuna_alerts"
DEFAULT_INTERVAL_MINUTES = 10
logger = logging.getLogger(__name__)


def _now() -> datetime:
    return models.utc_now()


def ensure_scheduler_schema(engine: Engine) -> None:
    """
    Migracion ligera para desarrollo con SQLite (donde Base.metadata.create_all
    no altera tablas ya existentes). En Postgres/produccion esto lo cubren las
    migraciones de Alembic.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    statements: list[str] = []

    if "scraper_runs" in existing_tables:
        columns = {column["name"] for column in inspector.get_columns("scraper_runs")}
        if "duration_seconds" not in columns:
            statements.append("ALTER TABLE scraper_runs ADD COLUMN duration_seconds INTEGER")
        if "new_offers" not in columns:
            statements.append("ALTER TABLE scraper_runs ADD COLUMN new_offers INTEGER")
        if "new_matches" not in columns:
            statements.append("ALTER TABLE scraper_runs ADD COLUMN new_matches INTEGER")

    if "notification_logs" in existing_tables:
        columns = {column["name"] for column in inspector.get_columns("notification_logs")}
        if "user_oferta_id" not in columns:
            statements.append("ALTER TABLE notification_logs ADD COLUMN user_oferta_id INTEGER")
        if "channel_id" not in columns:
            statements.append("ALTER TABLE notification_logs ADD COLUMN channel_id INTEGER")
        if "channel_type" not in columns:
            statements.append("ALTER TABLE notification_logs ADD COLUMN channel_type VARCHAR")
        if "destination" not in columns:
            statements.append("ALTER TABLE notification_logs ADD COLUMN destination VARCHAR")
        if "error_message" not in columns:
            statements.append("ALTER TABLE notification_logs ADD COLUMN error_message TEXT")
        if "sent_at" not in columns:
            statements.append("ALTER TABLE notification_logs ADD COLUMN sent_at DATETIME")

    if "users" in existing_tables:
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "puesto_deseado" not in columns:
            statements.append("ALTER TABLE users ADD COLUMN puesto_deseado VARCHAR")
        if "ubicacion_preferida" not in columns:
            statements.append("ALTER TABLE users ADD COLUMN ubicacion_preferida VARCHAR")
        if "modalidad_preferida" not in columns:
            statements.append("ALTER TABLE users ADD COLUMN modalidad_preferida VARCHAR")
        if "nivel_experiencia" not in columns:
            statements.append("ALTER TABLE users ADD COLUMN nivel_experiencia VARCHAR")
        if "bio" not in columns:
            statements.append("ALTER TABLE users ADD COLUMN bio TEXT")
        if "channel" in columns:
            # La columna "channel" pasa a ser opcional (legacy); nada que hacer en SQLite,
            # ya se crea nullable en el esquema actual de modelos.
            pass

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _clean_filter(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized or normalized.lower() == "cualquiera":
        return None
    return normalized


def _should_search_adzuna(alert: models.Alert) -> bool:
    source = (alert.fuente or "Cualquiera").strip().lower()
    return source in {"cualquiera", "adzuna"}


def _offer_url(offer_data: dict[str, Any]) -> str | None:
    value = offer_data.get("enlace") or offer_data.get("url") or offer_data.get("id")
    return str(value).strip() if value else None


def _build_job_offer(offer_data: dict[str, Any], url: str) -> models.JobOffer:
    return models.JobOffer(
        titulo=offer_data.get("titulo") or offer_data.get("title") or "Sin titulo",
        empresa=offer_data.get("empresa") or offer_data.get("company") or "Empresa confidencial",
        ubicacion=offer_data.get("ubicacion") or offer_data.get("location") or "No especificado",
        modalidad=offer_data.get("modalidad") or "No especificado",
        salario=offer_data.get("salario") or offer_data.get("salary") or "No especificado",
        descripcion=offer_data.get("descripcion"),
        enlace=url,
        fuente=offer_data.get("fuente") or offer_data.get("source") or "Adzuna",
        estado=offer_data.get("estado") or "guardado",
        fecha_publicacion=offer_data.get("fecha_publicacion"),
    )


def _scan_alert(
    db: Session,
    alert: models.Alert,
    search_func: Callable[..., list[dict[str, Any]]],
) -> tuple[int, int, int]:
    """
    Busca ofertas para una alerta, las guarda, crea los matches por usuario
    y dispara la notificacion por sus canales activos.
    Devuelve (ofertas_encontradas, ofertas_nuevas, matches_nuevos).
    """
    offers_found = 0
    new_offers = 0
    new_matches = 0

    offers = search_func(
        keyword=alert.termino,
        provincia=_clean_filter(alert.ubicacion),
        modalidad=_clean_filter(alert.modalidad),
        fuente="Adzuna",
        limit=10,
    )
    offers_found += len(offers)

    for offer_data in offers:
        url = _offer_url(offer_data)
        if not url:
            continue

        db_offer = db.query(models.JobOffer).filter(models.JobOffer.enlace == url).first()
        if db_offer is None:
            db_offer = _build_job_offer(offer_data, url)
            db.add(db_offer)
            db.flush()
            new_offers += 1

        # Evita duplicar el match si este usuario ya vio esta oferta
        existing_match = (
            db.query(models.UserOferta)
            .filter(
                models.UserOferta.user_id == alert.user_id,
                models.UserOferta.oferta_id == db_offer.id,
            )
            .first()
        )
        if existing_match:
            continue

        user_oferta = models.UserOferta(
            user_id=alert.user_id,
            oferta_id=db_offer.id,
            alerta_id=alert.id,
            estado="guardado",
            matched_at=_now(),
        )
        db.add(user_oferta)
        db.flush()
        new_matches += 1

        offer_dict = {
            "titulo": db_offer.titulo,
            "empresa": db_offer.empresa,
            "ubicacion": db_offer.ubicacion,
            "modalidad": db_offer.modalidad,
            "salario": db_offer.salario,
            "fuente": db_offer.fuente,
            "enlace": db_offer.enlace,
        }
        try:
            notify_user_offer(db, user_oferta, offer_dict)
        except Exception as notify_error:
            logger.exception("Offer notification failed for user %s: %s", alert.user_id, notify_error)

    return offers_found, new_offers, new_matches


def scan_single_alert(
    db: Session,
    alert: models.Alert,
    search_func: Callable[..., list[dict[str, Any]]] = search_adzuna_offers,
) -> models.ScraperRun:
    """
    Ejecuta una busqueda inmediata para UNA sola alerta (p.ej. justo despues
    de crearla), sin esperar al siguiente intervalo del scheduler.
    """
    started_at = _now()
    try:
        if not _should_search_adzuna(alert):
            offers_found, new_offers, new_matches = 0, 0, 0
        else:
            offers_found, new_offers, new_matches = _scan_alert(db, alert, search_func)

        finished_at = _now()
        scraper_run = models.ScraperRun(
            source="Adzuna",
            status="success",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=int((finished_at - started_at).total_seconds()),
            offers_found=offers_found,
            new_offers=new_offers,
            new_matches=new_matches,
            error_message=None,
        )
        db.add(scraper_run)
        db.commit()
        db.refresh(scraper_run)
        return scraper_run
    except Exception as exc:
        db.rollback()
        finished_at = _now()
        scraper_run = models.ScraperRun(
            source="Adzuna",
            status="error",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=int((finished_at - started_at).total_seconds()),
            offers_found=0,
            new_offers=0,
            new_matches=0,
            error_message=str(exc),
        )
        db.add(scraper_run)
        db.commit()
        db.refresh(scraper_run)
        return scraper_run


def run_scheduled_scraper(
    db: Session | None = None,
    search_func: Callable[..., list[dict[str, Any]]] = search_adzuna_offers,
) -> models.ScraperRun:
    owns_session = db is None
    db = db or SessionLocal()
    started_at = _now()
    offers_found = 0
    new_offers = 0
    new_matches = 0
    status = "success"
    error_message = None

    try:
        active_alerts = db.query(models.Alert).filter(models.Alert.activo.is_(True)).all()
        for alert in active_alerts:
            if not _should_search_adzuna(alert):
                continue

            alert_offers_found, alert_new_offers, alert_new_matches = _scan_alert(
                db, alert, search_func
            )
            offers_found += alert_offers_found
            new_offers += alert_new_offers
            new_matches += alert_new_matches

        finished_at = _now()
        scraper_run = models.ScraperRun(
            source="Adzuna",
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=int((finished_at - started_at).total_seconds()),
            offers_found=offers_found,
            new_offers=new_offers,
            new_matches=new_matches,
            error_message=error_message,
        )
        db.add(scraper_run)
        db.commit()
        db.refresh(scraper_run)
        return scraper_run
    except Exception as exc:
        db.rollback()
        finished_at = _now()
        scraper_run = models.ScraperRun(
            source="Adzuna",
            status="error",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=int((finished_at - started_at).total_seconds()),
            offers_found=offers_found,
            new_offers=new_offers,
            new_matches=new_matches,
            error_message=str(exc),
        )
        db.add(scraper_run)
        db.commit()
        db.refresh(scraper_run)
        return scraper_run
    finally:
        if owns_session:
            db.close()


class JobRadarScheduler:
    def __init__(self, session_factory: sessionmaker = SessionLocal) -> None:
        self.session_factory = session_factory
        self.scheduler = BackgroundScheduler(timezone="UTC")

    @property
    def enabled(self) -> bool:
        return os.getenv("SCRAPER_SCHEDULER_ENABLED", "true").lower() == "true"

    @property
    def interval_minutes(self) -> int:
        raw_value = os.getenv("SCRAPER_INTERVAL_MINUTES", str(DEFAULT_INTERVAL_MINUTES))
        try:
            return max(int(raw_value), 1)
        except ValueError:
            return DEFAULT_INTERVAL_MINUTES

    def start(self) -> None:
        if not self.enabled or self.scheduler.running:
            return

        self.scheduler.add_job(
            self.run_once,
            "interval",
            minutes=self.interval_minutes,
            id=SCHEDULER_JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def run_once(self) -> models.ScraperRun:
        db = self.session_factory()
        try:
            return run_scheduled_scraper(db=db)
        finally:
            db.close()

    def next_run_time(self) -> datetime | None:
        job = self.scheduler.get_job(SCHEDULER_JOB_ID)
        return job.next_run_time if job else None

    def state(self) -> str:
        states = {
            STATE_RUNNING: "running",
            STATE_PAUSED: "paused",
            STATE_STOPPED: "stopped",
        }
        if not self.enabled:
            return "disabled"
        return states.get(self.scheduler.state, "unknown")


scheduler_service = JobRadarScheduler()


def get_scheduler_status(db: Session) -> dict[str, Any]:
    last_run = (
        db.query(models.ScraperRun)
        .order_by(models.ScraperRun.started_at.desc(), models.ScraperRun.id.desc())
        .first()
    )
    execution_count = db.query(models.ScraperRun).count()
    next_run = scheduler_service.next_run_time()

    return {
        "last_run": {
            "id": last_run.id,
            "source": last_run.source,
            "status": last_run.status,
            "started_at": last_run.started_at,
            "finished_at": last_run.finished_at,
            "duration_seconds": last_run.duration_seconds,
            "offers_found": last_run.offers_found,
            "new_offers": last_run.new_offers,
            "new_matches": last_run.new_matches,
            "error_message": last_run.error_message,
        }
        if last_run
        else None,
        "next_run": next_run,
        "execution_count": execution_count,
        "status": scheduler_service.state(),
    }
