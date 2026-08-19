import logging
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models

logger = logging.getLogger(__name__)


def enqueue_alert_scan(db: Session, alert_id: int) -> models.AlertScanJob:
    dedupe_key = f"alert:{alert_id}"
    existing = (
        db.query(models.AlertScanJob)
        .filter(models.AlertScanJob.dedupe_key == dedupe_key)
        .first()
    )
    if existing:
        return existing

    job = models.AlertScanJob(alert_id=alert_id, dedupe_key=dedupe_key)
    try:
        with db.begin_nested():
            db.add(job)
            db.flush()
        return job
    except IntegrityError:
        return (
            db.query(models.AlertScanJob)
            .filter(models.AlertScanJob.dedupe_key == dedupe_key)
            .one()
        )


def enqueue_active_alert_scans(db: Session) -> int:
    alert_ids = [
        row[0]
        for row in db.query(models.Alert.id).filter(models.Alert.activo.is_(True)).all()
    ]
    before = db.query(models.AlertScanJob).filter(models.AlertScanJob.dedupe_key.isnot(None)).count()
    for alert_id in alert_ids:
        enqueue_alert_scan(db, alert_id)
    db.commit()
    after = db.query(models.AlertScanJob).filter(models.AlertScanJob.dedupe_key.isnot(None)).count()
    return max(after - before, 0)


def process_alert_scan_jobs(
    db: Session,
    scanner: Callable[[Session, models.Alert], models.ScraperRun] | None = None,
    limit: int = 10,
    max_attempts: int = 5,
) -> int:
    if scanner is None:
        from .scheduler import scan_single_alert

        scanner = scan_single_alert

    current_time = models.utc_now()
    jobs = (
        db.query(models.AlertScanJob)
        .filter(
            models.AlertScanJob.status.in_(("pending", "running")),
            models.AlertScanJob.available_at <= current_time,
        )
        .order_by(models.AlertScanJob.id)
        .with_for_update(skip_locked=True)
        .limit(limit)
        .all()
    )
    processed = 0
    for job in jobs:
        job_id = job.id
        alert_id = job.alert_id
        attempts = job.attempts + 1
        job.status = "running"
        job.attempts = attempts
        job.started_at = current_time
        job.available_at = current_time + timedelta(minutes=15)
        db.commit()

        try:
            alert = db.get(models.Alert, alert_id)
            if alert is not None and alert.activo:
                result = scanner(db, alert)
                if result.status != "success":
                    raise RuntimeError(result.error_message or "La búsqueda de la alerta falló")
        except Exception as exc:
            logger.exception("Alert scan job %s failed", job_id)
            current = db.get(models.AlertScanJob, job_id)
            current.error_message = str(exc)
            if attempts >= max_attempts:
                current.status = "failed"
                current.finished_at = models.utc_now()
                current.dedupe_key = None
            else:
                current.status = "pending"
                current.available_at = models.utc_now() + timedelta(minutes=min(2**attempts, 60))
            db.commit()
        else:
            current = db.get(models.AlertScanJob, job_id)
            current.status = "completed"
            current.error_message = None
            current.finished_at = models.utc_now()
            current.dedupe_key = None
            db.commit()
        processed += 1
    return processed
