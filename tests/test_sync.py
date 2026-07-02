from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base
from app import main as main_module


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_run_sync_task_guarda_ofertas_y_notifica_solo_alertas_activas(monkeypatch):
    reset_database()
    monkeypatch.setattr(main_module, "SessionLocal", TestingSessionLocal)

    db = TestingSessionLocal()
    try:
        user = models.User(email="sync@example.com", password_hash="hashed")
        db.add(user)
        db.flush()
        db.add(
            models.Alerta(
                user_id=user.id,
                termino="python",
                ubicacion="Madrid",
                modalidad="Remoto",
                activo=True,
            )
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
        "fuente": "InfoJobs",
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
    sent_messages = []

    monkeypatch.setattr(main_module, "fetch_infojobs_offers", lambda query, limit: [matching_offer])
    monkeypatch.setattr(main_module, "fetch_indeed_offers", lambda query, limit: [non_matching_offer])
    monkeypatch.setattr(main_module, "send_telegram_notification", sent_messages.append)

    new_count = main_module.run_sync_task("python")

    db = TestingSessionLocal()
    try:
        assert new_count == 2
        assert db.query(models.Oferta).count() == 2
        assert len(sent_messages) == 1
        assert "Python Backend Developer" in sent_messages[0]
    finally:
        db.close()


def test_run_sync_task_no_duplica_ofertas_existentes(monkeypatch):
    reset_database()
    monkeypatch.setattr(main_module, "SessionLocal", TestingSessionLocal)

    offer = {
        "titulo": "Python Backend Developer",
        "empresa": "JobRadar Labs",
        "ubicacion": "Madrid",
        "modalidad": "Remoto",
        "salario": "No especificado",
        "descripcion": "APIs con FastAPI",
        "enlace": "https://example.com/python-duplicate",
        "fuente": "InfoJobs",
        "estado": "guardado",
        "fecha_publicacion": "2026-06-28",
    }
    sent_messages = []

    monkeypatch.setattr(main_module, "fetch_infojobs_offers", lambda query, limit: [offer])
    monkeypatch.setattr(main_module, "fetch_indeed_offers", lambda query, limit: [])
    monkeypatch.setattr(main_module, "send_telegram_notification", sent_messages.append)

    assert main_module.run_sync_task("python") == 1
    assert main_module.run_sync_task("python") == 0

    db = TestingSessionLocal()
    try:
        assert db.query(models.Oferta).count() == 1
        assert len(sent_messages) == 1
    finally:
        db.close()
