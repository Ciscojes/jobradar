from tests.db import TestingSessionLocal, reset_database
from app import models
from app.services import manual_sync as sync_module


def test_run_sync_task_guarda_ofertas_y_notifica_solo_alertas_activas(monkeypatch):
    reset_database()

    db = TestingSessionLocal()
    try:
        user = models.User(email="sync@example.com", password_hash="hashed")
        other_user = models.User(email="sync-other@example.com", password_hash="hashed")
        db.add_all([user, other_user])
        db.flush()
        user_id = user.id
        other_user_id = other_user.id
        db.add_all(
            [
                models.Alerta(
                user_id=user.id,
                termino="python",
                ubicacion="Madrid",
                modalidad="Remoto",
                activo=True,
                ),
                models.Alerta(
                    user_id=other_user.id,
                    termino="python",
                    ubicacion="Madrid",
                    modalidad="Remoto",
                    activo=True,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    matching_offer = {
        "titulo": "Python Backend Developer",
        "empresa": "JobRadar Labs",
        "ubicacion": "Madrid",
        "modalidad": "Remoto",
        "salario": "No especificado",
        "descripcion": "APIs con FastAPI",
        "enlace": "https://example.com/python-madrid",
        "fuente": "Adzuna",
        "estado": "guardado",
        "fecha_publicacion": "2026-06-28",
    }
    non_matching_offer = {
        "titulo": "React Frontend Developer",
        "empresa": "JobRadar Labs",
        "ubicacion": "Barcelona",
        "modalidad": "Presencial",
        "salario": "No especificado",
        "descripcion": "Interfaces web",
        "enlace": "https://example.com/react-barcelona",
        "fuente": "Indeed",
        "estado": "guardado",
        "fecha_publicacion": "2026-06-28",
    }
    new_count = sync_module.run_sync_task(
        "python",
        user_id=user_id,
        session_factory=TestingSessionLocal,
        adzuna_fetch=lambda query, limit: [matching_offer],
        indeed_fetch=lambda query, limit: [non_matching_offer],
    )

    db = TestingSessionLocal()
    try:
        assert new_count == 2
        assert db.query(models.Oferta).count() == 2
        assert db.query(models.NotificationOutbox).count() == 1
        assert db.query(models.UserOferta).filter_by(user_id=user_id).count() == 1
        assert db.query(models.UserOferta).filter_by(user_id=other_user_id).count() == 0
    finally:
        db.close()


def test_run_sync_task_no_duplica_ofertas_existentes(monkeypatch):
    reset_database()

    db = TestingSessionLocal()
    user = models.User(email="sync-duplicate@example.com", password_hash="hashed")
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    offer = {
        "titulo": "Python Backend Developer",
        "empresa": "JobRadar Labs",
        "ubicacion": "Madrid",
        "modalidad": "Remoto",
        "salario": "No especificado",
        "descripcion": "APIs con FastAPI",
        "enlace": "https://example.com/python-duplicate",
        "fuente": "Adzuna",
        "estado": "guardado",
        "fecha_publicacion": "2026-06-28",
    }
    def run():
        return sync_module.run_sync_task(
            "python",
            user_id=user_id,
            session_factory=TestingSessionLocal,
            adzuna_fetch=lambda query, limit: [offer],
            indeed_fetch=lambda query, limit: [],
        )

    assert run() == 1
    assert run() == 0

    db = TestingSessionLocal()
    try:
        assert db.query(models.Oferta).count() == 1
        assert db.query(models.NotificationOutbox).count() == 0
    finally:
        db.close()
