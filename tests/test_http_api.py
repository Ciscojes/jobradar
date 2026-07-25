import uuid

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from tests.db import TestingSessionLocal, reset_database


@pytest.fixture
def http_client():
    reset_database()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _authenticated_headers(client: TestClient) -> dict[str, str]:
    email = f"http-{uuid.uuid4().hex}@example.com"
    password = "una-clave-segura-123"
    register_response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def test_http_patch_alerta_es_parcial_y_expone_cabeceras_seguras(http_client):
    headers = _authenticated_headers(http_client)
    create_response = http_client.post(
        "/alertas/",
        headers=headers,
        json={
            "termino": "python",
            "ubicacion": "Madrid",
            "modalidad": "Remoto",
            "fuente": "Adzuna",
            "activo": True,
        },
    )
    assert create_response.status_code == 201
    alerta_id = create_response.json()["id"]

    patch_response = http_client.patch(
        f"/alertas/{alerta_id}",
        headers=headers,
        json={"termino": "fastapi"},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["termino"] == "fastapi"
    assert patch_response.json()["ubicacion"] == "Madrid"
    assert patch_response.json()["modalidad"] == "Remoto"
    assert patch_response.headers["x-content-type-options"] == "nosniff"
    assert patch_response.headers["x-frame-options"] == "DENY"


def test_http_telegram_no_permite_enumerar_chats_sin_enlace_privado(http_client):
    headers = _authenticated_headers(http_client)

    missing_link = http_client.get("/notificaciones/telegram/chats", headers=headers)
    forged_link = http_client.get(
        "/notificaciones/telegram/chats",
        headers=headers,
        params={"link_token": "a" * 32},
    )

    assert missing_link.status_code == 422
    assert forged_link.status_code == 400
