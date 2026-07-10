import pytest
from fastapi import HTTPException

from tests.db import TestingSessionLocal, engine, reset_database as reset_test_database
from app import models
from app.database import Base
from app.main import app, health_check, read_root
from app.deps import get_current_user
from app.routers.auth import login_user, read_me, register_user
from app.routers.alertas import (
    activar_alerta,
    create_alerta,
    delete_alerta,
    desactivar_alerta,
    read_alerta,
    read_alertas,
    update_alerta,
)
from app.routers.ofertas import create_oferta, read_oferta, read_ofertas, update_oferta_estado
from app.schemas import (
    AlertaCreate,
    AlertaUpdate,
    OfertaCreate,
    OfertaUpdateEstado,
    UserCreate,
    UserLogin,
)


Base.metadata.create_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def reset_database():
    reset_test_database()
    yield
    app.dependency_overrides.clear()


def test_api_inicia_correctamente():
    assert app.title == "jobradar API"


def test_endpoint_principal_responde():
    response = read_root()

    assert response["status"] == "online"


def test_health_check_valida_base_de_datos(db_session):
    response = health_check(db=db_session)

    assert response["status"] == "ok"
    assert response["database"] == "ok"


def test_registro_login_y_usuario_autenticado(db_session):
    registered_user = register_user(
        UserCreate(
            email="USER@Example.com",
            password="supersecret",
            nombre="User Test",
        ),
        db=db_session,
    )

    assert registered_user.email == "user@example.com"
    assert registered_user.password_hash != "supersecret"

    token_payload = login_user(
        UserLogin(email="user@example.com", password="supersecret"),
        db=db_session,
    )

    assert token_payload.token_type == "bearer"
    assert token_payload.access_token

    current_user = get_current_user(
        token_payload.access_token,
        db=db_session,
    )
    me_response = read_me(current_user)

    assert me_response.email == "user@example.com"


def test_rutas_protegidas_declaran_get_current_user():
    protected_paths = {
        "/ofertas/",
        "/ofertas/{oferta_id}",
        "/ofertas/{oferta_id}/estado",
        "/alertas/",
        "/alertas/{alerta_id}",
        "/alertas/{alerta_id}/activar",
        "/alertas/{alerta_id}/desactivar",
        "/scheduler/status",
        "/scraper/sync",
    }

    protected_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) in protected_paths
    ]

    assert protected_routes
    for route in protected_routes:
        dependencies = [dependant.call for dependant in route.dependant.dependencies]
        assert get_current_user in dependencies


def test_endpoint_ofertas_responde_y_lista_ofertas(db_session):
    response = read_ofertas(db=db_session)

    assert isinstance(response, list)


def test_crear_y_listar_oferta(db_session):
    payload = OfertaCreate(**{
        "titulo": "Backend Python Developer",
        "empresa": "JobRadar Labs",
        "ubicacion": "Madrid",
        "modalidad": "Remoto",
        "salario": "No especificado",
        "descripcion": "Desarrollo de APIs con FastAPI.",
        "enlace": "https://example.com/ofertas/backend-python-developer",
        "fuente": "Test",
        "estado": "guardado",
        "fecha_publicacion": "2026-06-28",
    })

    created_offer = create_oferta(payload, db=db_session)

    assert created_offer.titulo == payload.titulo
    assert created_offer.empresa == payload.empresa
    assert created_offer.id is not None

    list_response = read_ofertas(db=db_session)
    assert any(offer.enlace == payload.enlace for offer in list_response)


def test_listado_ofertas_respeta_limite(db_session):
    for index in range(3):
        db_session.add(
            models.Oferta(
                titulo=f"Oferta {index}",
                empresa="JobRadar Labs",
                ubicacion="Madrid",
                modalidad="Remoto",
                salario="No especificado",
                descripcion="Desarrollo de APIs con FastAPI.",
                enlace=f"https://example.com/ofertas/limit-{index}",
                fuente="Test",
                estado="guardado",
            )
        )
    db_session.commit()

    response = read_ofertas(limit=2, db=db_session)

    assert len(response) == 2


def test_usuario_solo_lee_sus_ofertas_asociadas(db_session):
    user_a = models.User(email="offers-a@example.com", password_hash="hashed")
    user_b = models.User(email="offers-b@example.com", password_hash="hashed")
    offer_a = models.Oferta(
        titulo="Oferta usuario A",
        empresa="JobRadar Labs",
        ubicacion="Madrid",
        modalidad="Remoto",
        salario="No especificado",
        descripcion="Oferta privada para usuario A.",
        enlace="https://example.com/ofertas/user-a",
        fuente="Test",
        estado="guardado",
    )
    offer_b = models.Oferta(
        titulo="Oferta usuario B",
        empresa="JobRadar Labs",
        ubicacion="Barcelona",
        modalidad="Remoto",
        salario="No especificado",
        descripcion="Oferta privada para usuario B.",
        enlace="https://example.com/ofertas/user-b",
        fuente="Test",
        estado="guardado",
    )
    db_session.add_all([user_a, user_b, offer_a, offer_b])
    db_session.flush()
    db_session.add_all(
        [
            models.UserOferta(user_id=user_a.id, oferta_id=offer_a.id),
            models.UserOferta(user_id=user_b.id, oferta_id=offer_b.id),
        ]
    )
    db_session.commit()

    response = read_ofertas(db=db_session, current_user=user_a)

    assert [offer.id for offer in response] == [offer_a.id]
    with pytest.raises(HTTPException) as exc_info:
        read_oferta(offer_b.id, db=db_session, current_user=user_a)
    assert exc_info.value.status_code == 404


def test_actualizar_estado_oferta(db_session):
    payload = OfertaCreate(**{
        "titulo": "Backend Python Developer",
        "empresa": "JobRadar Labs",
        "ubicacion": "Madrid",
        "modalidad": "Remoto",
        "salario": "No especificado",
        "descripcion": "Desarrollo de APIs con FastAPI.",
        "enlace": "https://example.com/ofertas/backend-python-state",
        "fuente": "Test",
        "estado": "guardado",
        "fecha_publicacion": "2026-06-28",
    })
    created = create_oferta(payload, db=db_session)

    response = update_oferta_estado(
        created.id,
        OfertaUpdateEstado(estado="aplicado"),
        db=db_session,
    )

    assert response.estado == "aplicado"


def test_estado_oferta_es_independiente_por_usuario(db_session):
    user_a = models.User(email="state-a@example.com", password_hash="hashed")
    user_b = models.User(email="state-b@example.com", password_hash="hashed")
    offer = models.Oferta(
        titulo="Oferta compartida",
        empresa="JobRadar Labs",
        ubicacion="Madrid",
        enlace="https://example.com/ofertas/shared-state",
        fuente="Test",
        estado="guardado",
    )
    db_session.add_all([user_a, user_b, offer])
    db_session.flush()
    match_a = models.UserOferta(user_id=user_a.id, oferta_id=offer.id, estado="guardado")
    match_b = models.UserOferta(user_id=user_b.id, oferta_id=offer.id, estado="guardado")
    db_session.add_all([match_a, match_b])
    db_session.commit()

    response = update_oferta_estado(
        offer.id,
        OfertaUpdateEstado(estado="aplicado"),
        db=db_session,
        current_user=user_a,
    )

    db_session.refresh(offer)
    db_session.refresh(match_a)
    db_session.refresh(match_b)
    assert response.estado == "aplicado"
    assert offer.estado == "guardado"
    assert match_a.estado == "aplicado"
    assert match_b.estado == "guardado"
    assert read_oferta(offer.id, db=db_session, current_user=user_a).estado == "aplicado"
    assert read_oferta(offer.id, db=db_session, current_user=user_b).estado == "guardado"
    assert [item.id for item in read_ofertas(
        estado="aplicado", db=db_session, current_user=user_a
    )] == [offer.id]
    assert read_ofertas(estado="aplicado", db=db_session, current_user=user_b) == []


def test_crear_y_borrar_alerta(db_session):
    current_user = models.User(email="alerts@example.com", password_hash="hashed")
    db_session.add(current_user)
    db_session.commit()
    db_session.refresh(current_user)

    payload = AlertaCreate(**{
        "termino": "python",
        "ubicacion": "Madrid",
        "modalidad": "Remoto",
        "activo": True,
    })

    created_alert = create_alerta(payload, db=db_session, current_user=current_user)
    assert created_alert.id is not None
    assert created_alert.user_id == current_user.id

    list_response = read_alertas(db=db_session, current_user=current_user)
    assert any(alert.id == created_alert.id for alert in list_response)

    delete_response = delete_alerta(created_alert.id, db=db_session, current_user=current_user)
    assert delete_response is None


def test_listado_alertas_respeta_limite_y_usuario(db_session):
    user_a = models.User(email="alerts-a@example.com", password_hash="hashed")
    user_b = models.User(email="alerts-b@example.com", password_hash="hashed")
    db_session.add_all([user_a, user_b])
    db_session.flush()

    for index in range(3):
        db_session.add(
            models.Alerta(
                user_id=user_a.id,
                termino=f"python-{index}",
                ubicacion="Madrid",
                modalidad="Remoto",
                activo=True,
            )
        )
    db_session.add(
        models.Alerta(
            user_id=user_b.id,
            termino="react",
            ubicacion="Barcelona",
            modalidad="Remoto",
            activo=True,
        )
    )
    db_session.commit()

    response = read_alertas(limit=2, db=db_session, current_user=user_a)

    assert len(response) == 2
    assert all(alert.user_id == user_a.id for alert in response)


def test_crud_completo_alertas(db_session):
    current_user = models.User(email="crud-alerts@example.com", password_hash="hashed")
    db_session.add(current_user)
    db_session.commit()
    db_session.refresh(current_user)

    created_alert = create_alerta(
        AlertaCreate(
            termino="python",
            ubicacion="Madrid",
            categoria="Backend",
            salario_minimo=30000,
            modalidad="Remoto",
            fuente="Adzuna",
            activo=True,
        ),
        db=db_session,
        current_user=current_user,
    )

    found_alert = read_alerta(created_alert.id, db=db_session, current_user=current_user)
    assert found_alert.id == created_alert.id

    updated_alert = update_alerta(
        created_alert.id,
        AlertaUpdate(
            termino="fastapi",
            ubicacion="Barcelona",
            categoria="API",
            salario_minimo=35000,
            modalidad="Hibrido",
            fuente="Indeed",
            activo=True,
        ),
        db=db_session,
        current_user=current_user,
    )
    assert updated_alert.termino == "fastapi"
    assert updated_alert.ubicacion == "Barcelona"
    assert updated_alert.salario_minimo == 35000

    disabled_alert = desactivar_alerta(
        created_alert.id,
        db=db_session,
        current_user=current_user,
    )
    assert disabled_alert.activo is False

    enabled_alert = activar_alerta(
        created_alert.id,
        db=db_session,
        current_user=current_user,
    )
    assert enabled_alert.activo is True


def test_usuario_no_puede_acceder_alertas_de_otro_usuario(db_session):
    owner = models.User(email="owner-alerts@example.com", password_hash="hashed")
    other_user = models.User(email="other-alerts@example.com", password_hash="hashed")
    db_session.add_all([owner, other_user])
    db_session.commit()
    db_session.refresh(owner)
    db_session.refresh(other_user)

    created_alert = create_alerta(
        AlertaCreate(termino="python"),
        db=db_session,
        current_user=owner,
    )

    with pytest.raises(Exception) as read_error:
        read_alerta(created_alert.id, db=db_session, current_user=other_user)
    assert read_error.value.status_code == 404

    assert read_alertas(db=db_session, current_user=other_user) == []

    with pytest.raises(Exception) as update_error:
        update_alerta(
            created_alert.id,
            AlertaUpdate(termino="fastapi"),
            db=db_session,
            current_user=other_user,
        )
    assert update_error.value.status_code == 404


def test_modelos_saas_basicos(db_session):
    user = models.User(email="models@example.com", password_hash="hashed")
    db_session.add(user)
    db_session.flush()

    alert = models.Alert(
        user_id=user.id,
        keyword="python",
        provincia="Madrid",
        categoria="Tecnologia",
        salario_minimo=30000,
        modalidad="Remoto",
        fuente="Adzuna",
    )
    job_offer = models.JobOffer(
        title="Python Developer",
        company="JobRadar Labs",
        location="Madrid",
        salary="30000",
        source="Adzuna",
        url="https://example.com/python-model",
    )
    db_session.add_all([alert, job_offer])
    db_session.flush()

    notification = models.NotificationLog(
        user_id=user.id,
        alert_id=alert.id,
        job_offer_id=job_offer.id,
        channel="simulated",
        status="pending",
        message="Notificacion simulada",
    )
    scraper_run = models.ScraperRun(source="Adzuna", status="success", offers_found=1)
    db_session.add_all([notification, scraper_run])
    db_session.commit()

    db_session.refresh(user)
    assert user.alerts[0].keyword == "python"
    assert notification.alert_id == alert.id
    assert scraper_run.offers_found == 1
