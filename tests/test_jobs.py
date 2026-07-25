from datetime import timedelta
from importlib import import_module

from app import models
from app.main import sync_scraper
from tests.db import TestingSessionLocal, reset_database


def _create_match(db):
    user = models.User(email="outbox@example.com", password_hash="hashed")
    offer = models.JobOffer(
        titulo="Backend Python",
        empresa="JobRadar",
        ubicacion="Madrid",
        enlace="https://example.com/outbox-offer",
        fuente="Test",
    )
    db.add_all([user, offer])
    db.flush()
    match = models.UserOferta(user_id=user.id, oferta_id=offer.id)
    db.add(match)
    db.flush()
    return match


def test_encolar_notificacion_es_idempotente():
    reset_database()
    notifications = import_module("app.services.notifications")
    db = TestingSessionLocal()
    try:
        match = _create_match(db)

        first = notifications.enqueue_offer_notification(db, match)
        second = notifications.enqueue_offer_notification(db, match)
        db.commit()

        assert first.id == second.id
        assert db.query(models.NotificationOutbox).count() == 1
        assert first.status == "pending"
        assert first.attempts == 0
    finally:
        db.close()


def test_outbox_reintenta_sin_mantener_transaccion_durante_envio():
    reset_database()
    notifications = import_module("app.services.notifications")
    db = TestingSessionLocal()
    transaction_states = []
    try:
        match = _create_match(db)
        db.add(
            models.NotificationChannel(
                user_id=match.user_id,
                type="telegram",
                destination="123456",
                verified_at=models.utc_now(),
            )
        )
        outbox = notifications.enqueue_offer_notification(db, match)
        db.commit()

        def failing_sender(text, chat_id=None):
            transaction_states.append(db.in_transaction())
            return False, "failed", "Telegram temporalmente no disponible"

        processed = notifications.process_notification_outbox(db, sender=failing_sender)
        db.refresh(outbox)

        assert processed == 1
        assert transaction_states == [False]
        assert outbox.status == "pending"
        assert outbox.attempts == 1
        assert outbox.available_at > outbox.created_at
        assert "Telegram" in outbox.last_error
    finally:
        db.close()


def test_outbox_recupera_un_trabajo_abandonado_por_caida():
    reset_database()
    notifications = import_module("app.services.notifications")
    db = TestingSessionLocal()
    try:
        match = _create_match(db)
        db.add(
            models.NotificationChannel(
                user_id=match.user_id,
                type="telegram",
                destination="654321",
                verified_at=models.utc_now(),
            )
        )
        outbox = notifications.enqueue_offer_notification(db, match)
        outbox.status = "processing"
        outbox.available_at = models.utc_now() - timedelta(minutes=1)
        db.commit()

        processed = notifications.process_notification_outbox(
            db,
            sender=lambda text, chat_id=None: (True, "sent", None),
        )
        db.refresh(outbox)

        assert processed == 1
        assert outbox.status == "sent"
    finally:
        db.close()


def test_creacion_idempotente_devuelve_match_existente():
    reset_database()
    persistence = import_module("app.services.persistence")
    db = TestingSessionLocal()
    try:
        match = _create_match(db)
        db.commit()

        repeated, created = persistence.get_or_create_user_offer(
            db,
            user_id=match.user_id,
            offer_id=match.oferta_id,
            alert_id=None,
        )

        assert created is False
        assert repeated.id == match.id
        assert db.query(models.UserOferta).count() == 1
    finally:
        db.close()


def test_sincronizacion_manual_se_encola_de_forma_persistente():
    reset_database()
    manual_sync = import_module("app.services.manual_sync")
    db = TestingSessionLocal()
    try:
        user = models.User(email="manual-job@example.com", password_hash="hashed")
        db.add(user)
        db.flush()

        job = manual_sync.enqueue_manual_sync(db, user.id, "python")
        db.commit()

        assert job.id is not None
        assert job.status == "pending"
        assert job.query == "python"
        assert db.query(models.ManualSyncJob).count() == 1
    finally:
        db.close()


def test_worker_procesa_sincronizacion_manual_fuera_de_transaccion():
    reset_database()
    manual_sync = import_module("app.services.manual_sync")
    db = TestingSessionLocal()
    transaction_states = []
    try:
        user = models.User(email="manual-worker@example.com", password_hash="hashed")
        db.add(user)
        db.flush()
        job = manual_sync.enqueue_manual_sync(db, user.id, "fastapi")
        db.commit()
        expected_user_id = user.id

        def runner(query, user_id):
            transaction_states.append(db.in_transaction())
            assert query == "fastapi"
            assert user_id == expected_user_id
            return 0

        processed = manual_sync.process_manual_sync_jobs(db, runner=runner)
        db.refresh(job)

        assert processed == 1
        assert transaction_states == [False]
        assert job.status == "completed"
        assert job.finished_at is not None
        assert expected_user_id is not None
    finally:
        db.close()


def test_endpoint_sync_no_depende_de_background_tasks_del_proceso_web():
    reset_database()
    db = TestingSessionLocal()
    try:
        user = models.User(email="sync-endpoint@example.com", password_hash="hashed")
        db.add(user)
        db.commit()
        response = sync_scraper(
            query="python",
            current_user=user,
            db=db,
            _=None,
        )

        assert response["status"] == "queued"
        assert db.query(models.ManualSyncJob).count() == 1
    finally:
        db.close()


def test_mantenimiento_worker_actualiza_heartbeat_y_procesa_colas():
    reset_database()
    scheduler = import_module("app.services.scheduler")
    db = TestingSessionLocal()
    calls = []
    try:
        result = scheduler.run_worker_maintenance(
            db,
            manual_processor=lambda session: calls.append("manual") or 2,
            outbox_processor=lambda session: calls.append("outbox") or 3,
        )

        heartbeat = db.query(models.WorkerHeartbeat).one()
        assert calls == ["manual", "outbox"]
        assert result == {"manual_jobs": 2, "notifications": 3}
        assert heartbeat.worker_name == "scheduler"
        assert heartbeat.last_seen_at is not None
    finally:
        db.close()
