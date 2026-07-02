import base64
import os
from dataclasses import dataclass
from typing import Any

import requests


INFOJOBS_API_URL = "https://api.infojobs.net/api/7/offer"
INFOJOBS_SOURCE = "InfoJobs"


@dataclass(frozen=True)
class InfoJobsConfig:
    client_id: str | None
    client_secret: str | None
    redirect_uri: str | None

    @property
    def has_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret)


def get_infojobs_config() -> InfoJobsConfig:
    return InfoJobsConfig(
        client_id=os.getenv("INFOJOBS_CLIENT_ID") or None,
        client_secret=os.getenv("INFOJOBS_CLIENT_SECRET") or None,
        redirect_uri=os.getenv("INFOJOBS_REDIRECT_URI") or None,
    )


def build_auth_headers(config: InfoJobsConfig) -> dict[str, str]:
    if not config.client_id or not config.client_secret:
        return {}

    credentials = f"{config.client_id}:{config.client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json",
    }


def normalize_infojobs_offer(item: dict[str, Any], source: str = INFOJOBS_SOURCE) -> dict[str, Any]:
    teleworking = item.get("teleworking") or {}
    author = item.get("author") or {}

    return {
        "titulo": item.get("title") or "Sin titulo",
        "empresa": author.get("name") or "Empresa confidencial",
        "ubicacion": item.get("city") or item.get("province", {}).get("value") or "Espana",
        "modalidad": teleworking.get("name") or "No especificado",
        "salario": item.get("salaryDescription") or "No especificado",
        "descripcion": item.get("requirementMin") or "Sin descripcion detallada.",
        "enlace": item.get("link") or item.get("url") or "",
        "fuente": source,
        "estado": "guardado",
        "fecha_publicacion": item.get("published"),
    }


def get_mock_infojobs_offers(
    keyword: str = "python",
    provincia: str | None = None,
    modalidad: str | None = None,
    fuente: str = INFOJOBS_SOURCE,
    limit: int = 10,
) -> list[dict[str, Any]]:
    mock_data = [
        {
            "titulo": "Desarrollador Python Junior",
            "empresa": "TechMadrid Solutions",
            "ubicacion": "Madrid",
            "modalidad": "Hibrido",
            "salario": "24000 - 28000 EUR bruto/anio",
            "descripcion": "Perfil junior con Python, FastAPI y ganas de aprender.",
            "enlace": "https://www.infojobs.net/madrid/desarrollador-python-junior/of-i12345",
            "fuente": fuente,
            "estado": "guardado",
            "fecha_publicacion": "2026-06-25T10:00:00Z",
        },
        {
            "titulo": "Python Backend Developer",
            "empresa": "Global Software SL",
            "ubicacion": "Barcelona",
            "modalidad": "Remoto",
            "salario": "40000 - 45000 EUR bruto/anio",
            "descripcion": "Construccion de APIs eficientes en Python para producto SaaS.",
            "enlace": "https://www.infojobs.net/barcelona/python-backend-developer/of-i67890",
            "fuente": fuente,
            "estado": "guardado",
            "fecha_publicacion": "2026-06-26T14:30:00Z",
        },
        {
            "titulo": "Fullstack Developer Python React",
            "empresa": "Fintech Innova",
            "ubicacion": "Valencia",
            "modalidad": "Presencial",
            "salario": "30000 - 35000 EUR bruto/anio",
            "descripcion": "Desarrollo fintech con FastAPI, Django y React.",
            "enlace": "https://www.infojobs.net/valencia/fullstack-developer/of-i11121",
            "fuente": fuente,
            "estado": "guardado",
            "fecha_publicacion": "2026-06-27T08:15:00Z",
        },
    ]

    keyword_value = (keyword or "").strip().lower()
    provincia_value = (provincia or "").strip().lower()
    modalidad_value = (modalidad or "").strip().lower()

    filtered = []
    for offer in mock_data:
        searchable = f"{offer['titulo']} {offer['descripcion']}".lower()
        if keyword_value and keyword_value not in searchable:
            continue
        if provincia_value and provincia_value not in offer["ubicacion"].lower():
            continue
        if modalidad_value and modalidad_value not in offer["modalidad"].lower():
            continue
        filtered.append(offer)

    if not filtered and keyword_value:
        filtered = [{**mock_data[0], "titulo": f"Oferta mock para {keyword}"}]

    return filtered[:limit]


def search_infojobs_offers(
    keyword: str = "python",
    provincia: str | None = None,
    modalidad: str | None = None,
    fuente: str = INFOJOBS_SOURCE,
    limit: int = 10,
) -> list[dict[str, Any]]:
    config = get_infojobs_config()
    if not config.has_credentials:
        return get_mock_infojobs_offers(keyword, provincia, modalidad, fuente, limit)

    params: dict[str, Any] = {
        "q": keyword,
        "maxResults": limit,
    }
    if provincia:
        params["province"] = provincia
    if modalidad:
        params["teleworking"] = modalidad

    try:
        response = requests.get(
            INFOJOBS_API_URL,
            headers=build_auth_headers(config),
            params=params,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException:
        return get_mock_infojobs_offers(keyword, provincia, modalidad, fuente, limit)

    data = response.json()
    items = data.get("items", [])
    offers = [normalize_infojobs_offer(item, source=fuente) for item in items]
    return [offer for offer in offers if offer["enlace"]][:limit]


def fetch_infojobs_offers(query: str = "python", limit: int = 10) -> list[dict[str, Any]]:
    return search_infojobs_offers(keyword=query, limit=limit)
