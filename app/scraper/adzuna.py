import os
from dataclasses import dataclass
from typing import Any

import requests


ADZUNA_API_BASE = "https://api.adzuna.com/v1/api/jobs"
ADZUNA_SOURCE = "Adzuna"


@dataclass(frozen=True)
class AdzunaConfig:
    app_id: str | None
    app_key: str | None
    country: str

    @property
    def has_credentials(self) -> bool:
        return bool(self.app_id and self.app_key)


def get_adzuna_config() -> AdzunaConfig:
    return AdzunaConfig(
        app_id=os.getenv("ADZUNA_APP_ID") or None,
        app_key=os.getenv("ADZUNA_APP_KEY") or None,
        country=(os.getenv("ADZUNA_COUNTRY") or "es").strip().lower(),
    )


def normalize_adzuna_offer(item: dict[str, Any], source: str = ADZUNA_SOURCE) -> dict[str, Any]:
    company = item.get("company") or {}
    location = item.get("location") or {}

    salary_min = item.get("salary_min")
    salary_max = item.get("salary_max")
    if salary_min and salary_max:
        salario = f"{int(salary_min):,} - {int(salary_max):,} EUR bruto/anio".replace(",", ".")
    else:
        salario = "No especificado"

    contract_time = (item.get("contract_time") or "").lower()
    if "part" in contract_time:
        modalidad = "Parcial"
    elif "full" in contract_time:
        modalidad = "Presencial"
    else:
        modalidad = "No especificado"

    return {
        "titulo": item.get("title") or "Sin titulo",
        "empresa": company.get("display_name") or "Empresa confidencial",
        "ubicacion": location.get("display_name") or "Espana",
        "modalidad": modalidad,
        "salario": salario,
        "descripcion": item.get("description") or "Sin descripcion detallada.",
        "enlace": item.get("redirect_url") or "",
        "fuente": source,
        "estado": "guardado",
        "fecha_publicacion": item.get("created"),
    }


def get_mock_adzuna_offers(
    keyword: str = "python",
    provincia: str | None = None,
    modalidad: str | None = None,
    fuente: str = ADZUNA_SOURCE,
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
            "enlace": "https://www.adzuna.es/details/madrid-python-junior-12345",
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
            "enlace": "https://www.adzuna.es/details/barcelona-python-backend-67890",
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
            "enlace": "https://www.adzuna.es/details/valencia-fullstack-11121",
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


def search_adzuna_offers(
    keyword: str = "python",
    provincia: str | None = None,
    modalidad: str | None = None,
    fuente: str = ADZUNA_SOURCE,
    limit: int = 10,
) -> list[dict[str, Any]]:
    config = get_adzuna_config()
    if not config.has_credentials:
        return get_mock_adzuna_offers(keyword, provincia, modalidad, fuente, limit)

    where = provincia
    if modalidad and modalidad.strip().lower() not in {"", "no especificado"}:
        # Adzuna no tiene un filtro nativo de modalidad; lo añadimos al termino
        # de busqueda como mejor esfuerzo (p.ej. "python remoto").
        keyword = f"{keyword} {modalidad}".strip()

    params: dict[str, Any] = {
        "app_id": config.app_id,
        "app_key": config.app_key,
        "results_per_page": limit,
        "what": keyword,
        "content-type": "application/json",
    }
    if where:
        params["where"] = where

    url = f"{ADZUNA_API_BASE}/{config.country}/search/1"

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return get_mock_adzuna_offers(keyword, provincia, modalidad, fuente, limit)

    data = response.json()
    items = data.get("results", [])
    offers = [normalize_adzuna_offer(item, source=fuente) for item in items]
    return [offer for offer in offers if offer["enlace"]][:limit]


def fetch_adzuna_offers(query: str = "python", limit: int = 10) -> list[dict[str, Any]]:
    return search_adzuna_offers(keyword=query, limit=limit)
