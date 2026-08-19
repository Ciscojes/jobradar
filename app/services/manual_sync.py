import logging
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy.orm import Session, sessionmaker

from .. import models
from ..database import SessionLocal
from ..scraper.adzuna import fetch_adzuna_offers
from ..scraper.indeed import fetch_indeed_offers
from .ingestion import match_offer_to_alert, offer_matches_alert, persist_offer

logger = logging.getLogger(__name__)


def enqueue_manual_sync(db: Session, user_id: int, query: str) -> models.ManualSyncJob:
    job = models.ManualSyncJob(user_id=user_id, query=query.strip())
    db.add(job)
    db.flush()
    return job


def run_sync_task(
    query: str,
    user_id: int,
    session_factory: sessionmaker = SessionLocal,
    adzuna_fetch: Callable[..., list[dict]] = fetch_adzuna_offers,
    indeed_fetch: Callable[..., list[dict]] = fetch_indeed_offers,
) -> int:
    offers = adzuna_fetch(query, limit=5) + indeed_fetch(query, limit=5)
    db = session_factory()
    new_offers = 0
    try:
        active_alerts = (
            db.query(models.Alert)
            .filter(models.Alert.user_id == user_id, models.Alert.activo.is_(True))
            .all()
        )
        for offer_data in offers:
            offer, offer_created = persist_offer(db, offer_data)
            if offer is None:
                continue
            new_offers += int(offer_created)
            for alert in active_alerts:
                if not offer_matches_alert(offer_data, alert):
                    continue
                match_offer_to_alert(db, offer, alert)
                break
        db.commit()
        return new_offers
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def process_manual_sync_jobs(
    db: Session,
    runner: Callable[[str, int], int] = run_sync_task,
    limit: int = 10,
    max_attempts: int = 5,
) -> int:
    current_time = models.utc_now()
    jobs = (
        db.query(models.ManualSyncJob)
        .filter(
            models.ManualSyncJob.status.in_(("pending", "running")),
            models.ManualSyncJob.available_at <= current_time,
        )
        .order_by(models.ManualSyncJob.id)
        .with_for_update(skip_locked=True)
        .limit(limit)
        .all()
    )
    processed = 0
    for job in jobs:
        job_id = job.id
        query = job.query
        user_id = job.user_id
        attempts = job.attempts + 1
        job.status = "running"
        job.attempts = attempts
        job.started_at = current_time
        job.available_at = current_time + timedelta(minutes=15)
        db.commit()

        try:
            runner(query, user_id)
        except Exception as exc:
            logger.exception("Manual sync job %s failed", job_id)
            current = db.get(models.ManualSyncJob, job_id)
            current.error_message = str(exc)
            if attempts >= max_attempts:
                current.status = "failed"
                current.finished_at = models.utc_now()
            else:
                current.status = "pending"
                current.available_at = models.utc_now() + timedelta(minutes=min(2**attempts, 60))
            db.commit()
        else:
            current = db.get(models.ManualSyncJob, job_id)
            current.status = "completed"
            current.error_message = None
            current.finished_at = models.utc_now()
            db.commit()
        processed += 1
    return processed
