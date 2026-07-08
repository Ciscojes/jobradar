import os

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["TELEGRAM_BOT_TOKEN"] = ""

from app import models
from app.database import Base
from app.deps import get_current_user
from app.routers.auth import login_user, register_user
from app.routers.notificaciones import (
    create_channel,
    delete_channel,
    read_channels,
    read_notification_logs,
    test_channel as call_test_channel,
    update_channel,
)
from app.schemas import NotificationChannelCreate, NotificationChannelUpdate, UserCreate, UserLogin
from app.services.scheduler import run_scheduled_scraper


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _crear_usuario_autenticado(db_session, email="canales@example.com"):
    register_user(
        UserCreate(email=email, password="supersegura123", nombre="Test"),
        db=db_session,
    )
    token_payload = login_user(UserLogin(email=email, password="supersegura123"), db=db_session)
    return get_current_user(token_payload.access_token, db=db_session)


def test_crud_canales_de_notificacion(db_session):
    user = _crear_usuario_autenticado(db_session)

    created = create_channel(
        NotificationChannelCreate(type="telegram", destination="123456", is_active=True),
        db=db_session,
        current_user=user,
    )
    assert created.id is not None
    assert created.type == "telegram"

    channels = read_channels(db=db_session, current_user=user)
    assert len(channels) == 1

    # Crear el canal ya dispara un mensaje de bienvenida automatico
    welcome_logs = read_notification_logs(db=db_session, current_user=user)
    assert len(welcome_logs) == 1
    assert welcome_logs[0].status == "simulated"

    result = call_test_channel(created.id, db=db_session, current_user=user)
    assert result["status"] == "sent"

    logs = read_notification_logs(db=db_session, current_user=user)
    assert len(logs) == 2
    assert logs[0].channel_type == "telegram"
    assert logs[0].destination == "123456"
    assert logs[0].status == "simulated"

    updated = update_channel(
        created.id,
        NotificationChannelUpdate(is_active=False),
        db=db_session,
        current_user=user,
    )
    assert updated.is_active is False

    delete_channel(created.id, db=db_session, current_user=user)
    assert read_channels(db=db_session, current_user=user) == []


def test_logs_de_notificacion_respetan_limite_y_usuario(db_session):
    user_a = _crear_usuario_autenticado(db_session, email="logs-a@example.com")
    user_b = _crear_usuario_autenticado(db_session, email="logs-b@example.com")

    for index in range(3):
        db_session.add(
            models.NotificationLog(
                user_id=user_a.id,
                channel_type="telegram",
                destination=str(index),
                status="simulated",
            )
        )
    db_session.add(
        models.NotificationLog(
            user_id=user_b.id,
            channel_type="telegram",
            destination="other",
            status="simulated",
        )
    )
    db_session.commit()

    logs = read_notification_logs(limit=2, db=db_session, current_user=user_a)

    assert len(logs) == 2
    assert all(log.user_id == user_a.id for log in logs)


def test_canales_respetan_limite(db_session):
    user = _crear_usuario_autenticado(db_session, email="channels-limit@example.com")

    for index in range(3):
        db_session.add(
            models.NotificationChannel(
                user_id=user.id,
                type="telegram",
                destination=str(index),
                is_active=True,
            )
        )
    db_session.commit()

    channels = read_channels(limit=2, db=db_session, current_user=user)

    assert len(channels) == 2


def test_tipo_de_canal_invalido_es_rechazado(db_session):
    user = _crear_usuario_autenticado(db_session, email="canal-invalido@example.com")

    with pytest.raises(HTTPException) as exc_info:
        create_channel(
            NotificationChannelCreate(type="whatsapp", destination="123456"),
            db=db_session,
            current_user=user,
        )
    assert exc_info.value.status_code == 400


def test_probar_canal_inactivo_es_rechazado(db_session):
    user = _crear_usuario_autenticado(db_session, email="canal-inactivo@example.com")

    created = create_channel(
        NotificationChannelCreate(type="email", destination="test@example.com", is_active=False),
        db=db_session,
        current_user=user,
    )

    with pytest.raises(HTTPException) as exc_info:
        call_test_channel(created.id, db=db_session, current_user=user)
    assert exc_info.value.status_code == 400


def test_scheduler_crea_match_y_notifica_por_canal_activo(db_session):
    user = models.User(email="scheduler-canal@example.com", password_hash="hashed")
    db_session.add(user)
    db_session.flush()

    db_session.add(
        models.NotificationChannel(
            user_id=user.id, type="telegram", destination="555555", is_active=True
        )
    )
    db_session.add(
        models.Alert(
            user_id=user.id,
            termino="python",
            ubicacion="Madrid",
            modalidad="Remoto",
            fuente="Adzuna",
            activo=True,
        )
    )
    db_session.commit()

    def fake_search(**kwargs):
        return [
            {
                "titulo": "Python Backend Developer",
                "empresa": "JobRadar Labs",
                "ubicacion": "Madrid",
                "modalidad": "Remoto",
                "salario": "No especificado",
                "enlace": "https://example.com/jobs/python-notif",
                "fuente": "Adzuna",
            }
        ]

    run = run_scheduled_scraper(db=db_session, search_func=fake_search)
    assert run.new_offers == 1
    assert run.new_matches == 1

    matches = db_session.query(models.UserOferta).filter(models.UserOferta.user_id == user.id).all()
    assert len(matches) == 1

    logs = (
        db_session.query(models.NotificationLog)
        .filter(models.NotificationLog.user_id == user.id)
        .all()
    )
    assert len(logs) == 1
    assert logs[0].channel_type == "telegram"
    assert logs[0].destination == "555555"

    # Segunda ejecucion: mismo match, no debe duplicar ni renotificar
    second_run = run_scheduled_scraper(db=db_session, search_func=fake_search)
    assert second_run.new_matches == 0

    matches_after = (
        db_session.query(models.UserOferta).filter(models.UserOferta.user_id == user.id).all()
    )
    assert len(matches_after) == 1

    logs_after = (
        db_session.query(models.NotificationLog)
        .filter(models.NotificationLog.user_id == user.id)
        .all()
    )
    assert len(logs_after) == 1
