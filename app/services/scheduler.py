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
from ..scraper.infojobs import search_infojobs_offers


SCHEDULER_JOB_ID = "jobradar_infojobs_alerts"
DEFAULT_INTERVAL_MINUTES = 10


def _now() -> datetime:
    return models.utc_now()


def ensure_scheduler_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if "scraper_runs" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("scraper_runs")}
    statements = []
    if "duration_seconds" not in columns:
        statements.append("ALTER TABLE scraper_runs ADD COLUMN duration_seconds INTEGER")
    if "new_offers" not in columns:
        statements.append("ALTER TABLE scraper_runs ADD COLUMN new_offers INTEGER")

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


def _should_search_infojobs(alert: models.Alert) -> bool:
    source = (alert.fuente or "Cualquiera").strip().lower()
    return source in {"cualquiera", "infojobs"}


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
        fuente=offer_data.get("fuente") or offer_data.get("source") or "InfoJobs",
        estado=offer_data.get("estado") or "guardado",
        fecha_publicacion=offer_data.get("fecha_publicacion"),
    )


def run_scheduled_scraper(
    db: Session | None = None,
    search_func: Callable[..., list[dict[str, Any]]] = search_infojobs_offers,
) -> models.ScraperRun:
    owns_session = db is None
    db = db or SessionLocal()
    started_at = _now()
    offers_found = 0
    new_offers = 0
    status = "success"
    error_message = None

    try:
        active_alerts = db.query(models.Alert).filter(models.Alert.activo.is_(True)).all()
        for alert in active_alerts:
            if not _should_search_infojobs(alert):
                continue

            offers = search_func(
                keyword=alert.termino,
                provincia=_clean_filter(alert.ubicacion),
                modalidad=_clean_filter(alert.modalidad),
                fuente="InfoJobs",
                limit=10,
            )
            offers_found += len(offers)

            for offer_data in offers:
                url = _offer_url(offer_data)
                if not url:
                    continue

                exists = db.query(models.JobOffer).filter(models.JobOffer.enlace == url).first()
                if exists:
                    continue

                db.add(_build_job_offer(offer_data, url))
                new_offers += 1

        finished_at = _now()
        scraper_run = models.ScraperRun(
            source="InfoJobs",
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=int((finished_at - started_at).total_seconds()),
            offers_found=offers_found,
            new_offers=new_offers,
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
            source="InfoJobs",
            status="error",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=int((finished_at - started_at).total_seconds()),
            offers_found=offers_found,
            new_offers=new_offers,
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
        "last_run": last_run,
        "next_run": next_run,
        "execution_count": execution_count,
        "status": scheduler_service.state(),
    }
