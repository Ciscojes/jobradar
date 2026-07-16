from tests.db import TestingSessionLocal, reset_database
from app import models
from app.services.scheduler import get_scheduler_status, run_scheduled_scraper


def test_scheduler_busca_alertas_activas_y_guarda_ofertas_sin_duplicar():
    reset_database()
    db = TestingSessionLocal()
    calls = []

    try:
        user = models.User(email="scheduler@example.com", password_hash="hashed")
        db.add(user)
        db.flush()

        active_alert = models.Alert(
            user_id=user.id,
            termino="python",
            ubicacion="Madrid",
            modalidad="Remoto",
            fuente="Adzuna",
            activo=True,
        )
        inactive_alert = models.Alert(
            user_id=user.id,
            termino="react",
            ubicacion="Barcelona",
            modalidad="Presencial",
            fuente="Adzuna",
            activo=False,
        )
        db.add_all([active_alert, inactive_alert])
        db.commit()

        def fake_search(**kwargs):
            calls.append(kwargs)
            return [
                {
                    "titulo": "Python Backend Developer",
                    "empresa": "JobRadar Labs",
                    "ubicacion": "Madrid",
                    "modalidad": "Remoto",
                    "salario": "No especificado",
                    "descripcion": "APIs con FastAPI",
                    "enlace": "https://example.com/jobs/python-backend",
                    "fuente": "Adzuna",
                    "estado": "guardado",
                    "fecha_publicacion": "2026-06-30",
                }
            ]

        first_run = run_scheduled_scraper(db=db, search_func=fake_search)
        second_run = run_scheduled_scraper(db=db, search_func=fake_search)

        assert len(calls) == 2
        assert calls[0]["keyword"] == "python"
        assert calls[0]["provincia"] == "Madrid"
        assert calls[0]["modalidad"] == "Remoto"
        assert first_run.status == "success"
        assert first_run.offers_found == 1
        assert first_run.new_offers == 1
        assert second_run.status == "success"
        assert second_run.offers_found == 1
        assert second_run.new_offers == 0
        assert db.query(models.JobOffer).count() == 1
        assert db.query(models.ScraperRun).count() == 2
    finally:
        db.close()


def test_scheduler_registra_error_de_ejecucion():
    reset_database()
    db = TestingSessionLocal()

    try:
        user = models.User(email="scheduler-error@example.com", password_hash="hashed")
        db.add(user)
        db.flush()
        db.add(
            models.Alert(
                user_id=user.id,
                termino="python",
                fuente="Adzuna",
                activo=True,
            )
        )
        db.commit()

        def failing_search(**kwargs):
            raise RuntimeError("Adzuna no disponible")

        scraper_run = run_scheduled_scraper(db=db, search_func=failing_search)

        assert scraper_run.status == "error"
        assert "Adzuna no disponible" in scraper_run.error_message
        assert scraper_run.finished_at is not None
        assert scraper_run.duration_seconds >= 0
    finally:
        db.close()


def test_scheduler_status_devuelve_ultima_ejecucion_y_conteo():
    reset_database()
    db = TestingSessionLocal()

    try:
        run_scheduled_scraper(db=db, search_func=lambda **kwargs: [])
        status = get_scheduler_status(db)

        assert status["last_run"]["status"] == "success"
        assert status["execution_count"] == 1
        assert "status" in status
        assert "next_run" in status
    finally:
        db.close()
