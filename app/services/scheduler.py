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
from ..rate_limit import cleanup_rate_limit_buckets
from .alert_scans import enqueue_active_alert_scans, process_alert_scan_jobs
from .manual_sync import process_manual_sync_jobs
from .notifications import process_notification_outbox
from .ingestion import ingest_offer_for_alert


SCHEDULER_JOB_ID = "jobradar_adzuna_alerts"
MAINTENANCE_JOB_ID = "jobradar_worker_maintenance"
DEFAULT_INTERVAL_MINUTES = 10
logger = logging.getLogger(__name__)


def _now() -> datetime:
    return models.utc_now()


def run_worker_maintenance(
    db: Session,
    manual_processor: Callable[[Session], int] = process_manual_sync_jobs,
    alert_processor: Callable[[Session], int] = process_alert_scan_jobs,
    outbox_processor: Callable[[Session], int] = process_notification_outbox,
) -> dict[str, int]:
    heartbeat = (
        db.query(models.WorkerHeartbeat)
        .filter(models.WorkerHeartbeat.worker_name == "scheduler")
        .first()
    )
    if heartbeat is None:
        heartbeat = models.WorkerHeartbeat(worker_name="scheduler")
        db.add(heartbeat)
    heartbeat.status = "running"
    heartbeat.last_seen_at = _now()
    db.commit()

    try:
        cleanup_rate_limit_buckets(db)
        manual_jobs = manual_processor(db)
        alert_jobs = alert_processor(db)
        notifications = outbox_processor(db)
    except Exception as exc:
        db.rollback()
        heartbeat = (
            db.query(models.WorkerHeartbeat)
            .filter(models.WorkerHeartbeat.worker_name == "scheduler")
            .one()
        )
        heartbeat.status = "error"
        heartbeat.last_error = str(exc)
        heartbeat.last_seen_at = _now()
        db.commit()
        raise

    heartbeat = (
        db.query(models.WorkerHeartbeat)
        .filter(models.WorkerHeartbeat.worker_name == "scheduler")
        .one()
    )
    heartbeat.status = "healthy"
    heartbeat.last_error = None
    heartbeat.last_seen_at = _now()
    heartbeat.manual_jobs_processed += manual_jobs
    heartbeat.alert_jobs_processed += alert_jobs
    heartbeat.notifications_processed += notifications
    db.commit()
    return {
        "manual_jobs": manual_jobs,
        "alert_jobs": alert_jobs,
        "notifications": notifications,
    }


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
        if "user_id" not in columns:
            statements.append("ALTER TABLE scraper_runs ADD COLUMN user_id INTEGER")
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
        if "auth_version" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0"
            )
        if "channel" in columns:
            # La columna "channel" pasa a ser opcional (legacy); nada que hacer en SQLite,
            # ya se crea nullable en el esquema actual de modelos.
            pass

    if "worker_heartbeats" in existing_tables:
        columns = {
            column["name"] for column in inspector.get_columns("worker_heartbeats")
        }
        if "alert_jobs_processed" not in columns:
            statements.append(
                "ALTER TABLE worker_heartbeats "
                "ADD COLUMN alert_jobs_processed INTEGER NOT NULL DEFAULT 0"
            )

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

    keyword = alert.termino
    province = _clean_filter(alert.ubicacion)
    modality = _clean_filter(alert.modalidad)
    db.commit()

    offers = search_func(
        keyword=keyword,
        provincia=province,
        modalidad=modality,
        fuente="Adzuna",
        limit=10,
    )
    offers_found += len(offers)

    for offer_data in offers:
        offer_created, match_created = ingest_offer_for_alert(db, offer_data, alert)
        new_offers += int(offer_created)
        new_matches += int(match_created)

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
            user_id=alert.user_id,
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
            user_id=alert.user_id,
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

    @property
    def poll_interval_seconds(self) -> int:
        raw_value = os.getenv("WORKER_POLL_INTERVAL_SECONDS", "30")
        try:
            return max(int(raw_value), 5)
        except ValueError:
            return 30

    def start(self) -> None:
        if self.scheduler.running:
            return

        if self.enabled:
            self.scheduler.add_job(
                self.run_once,
                "interval",
                minutes=self.interval_minutes,
                id=SCHEDULER_JOB_ID,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
        self.scheduler.add_job(
            self.run_maintenance,
            "interval",
            seconds=self.poll_interval_seconds,
            id=MAINTENANCE_JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def run_once(self) -> int:
        db = self.session_factory()
        try:
            return enqueue_active_alert_scans(db)
        finally:
            db.close()

    def run_maintenance(self) -> dict[str, int]:
        db = self.session_factory()
        try:
            return run_worker_maintenance(db)
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
    heartbeat = (
        db.query(models.WorkerHeartbeat)
        .filter(models.WorkerHeartbeat.worker_name == "scheduler")
        .first()
    )
    if heartbeat:
        current_time = _now()
        if heartbeat.last_seen_at.tzinfo is None:
            current_time = current_time.replace(tzinfo=None)
        age_seconds = max(int((current_time - heartbeat.last_seen_at).total_seconds()), 0)
        worker = {
            "status": heartbeat.status,
            "last_seen_at": heartbeat.last_seen_at,
            "last_error": heartbeat.last_error,
            "age_seconds": age_seconds,
            "is_stale": age_seconds > max(scheduler_service.poll_interval_seconds * 3, 120),
            "manual_jobs_processed": heartbeat.manual_jobs_processed,
            "alert_jobs_processed": heartbeat.alert_jobs_processed,
            "notifications_processed": heartbeat.notifications_processed,
        }
    else:
        worker = {
            "status": "unknown",
            "last_seen_at": None,
            "last_error": None,
            "age_seconds": None,
            "is_stale": True,
            "manual_jobs_processed": 0,
            "alert_jobs_processed": 0,
            "notifications_processed": 0,
        }
    queues = {
        "manual_pending": (
            db.query(models.ManualSyncJob)
            .filter(models.ManualSyncJob.status == "pending")
            .count()
        ),
        "alert_pending": (
            db.query(models.AlertScanJob)
            .filter(models.AlertScanJob.status == "pending")
            .count()
        ),
        "notifications_pending": (
            db.query(models.NotificationOutbox)
            .filter(models.NotificationOutbox.status == "pending")
            .count()
        ),
        "notifications_failed": (
            db.query(models.NotificationOutbox)
            .filter(models.NotificationOutbox.status == "failed")
            .count()
        ),
    }

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
        # El scheduler vive en otro proceso. La API solo puede informar de su
        # configuración y de las ejecuciones persistidas, no de su memoria local.
        "next_run": None,
        "execution_count": execution_count,
        "status": "enabled" if scheduler_service.enabled else "disabled",
        "worker": worker,
        "queues": queues,
    }
