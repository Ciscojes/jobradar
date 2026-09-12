import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import urllib.parse

from ..config import get_settings
from .http import get_with_retry

logger = logging.getLogger(__name__)

INDEED_SOURCE = "Indeed"


def _mock_or_raise(keyword: str, provincia: str | None, modalidad: str | None, fuente: str, limit: int, reason: str) -> List[Dict[str, Any]]:
    if get_settings().allow_mock_offers:
        return get_mock_indeed_offers(keyword, provincia, modalidad, fuente, limit)
    raise RuntimeError(f"Indeed no está disponible: {reason}")


def search_indeed_offers(
    keyword: str = "python",
    provincia: str | None = None,
    modalidad: str | None = None,
    fuente: str = INDEED_SOURCE,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Simula o realiza el raspado de ofertas en Indeed España.
    Dado que Indeed tiene protecciones antibot fuertes (Cloudflare), 
    se implementa una lógica de raspado base con fallback automático a datos simulados realistas.
    """
    encoded_query = urllib.parse.quote(keyword)

    # URL de búsqueda en Indeed España
    indeed_url = f"https://es.indeed.com/jobs?q={encoded_query}"
    if provincia:
        indeed_url += f"&l={urllib.parse.quote(provincia)}"
    else:
        indeed_url += "&l="
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
    }

    try:
        response = get_with_retry(
            indeed_url,
            headers=headers,
            timeout=10,
            request_get=requests.get,
        )
        # Si somos bloqueados o la respuesta no es 200, caemos al fallback de mock de forma segura
        if response.status_code != 200:
            return _mock_or_raise(keyword, provincia, modalidad, fuente, limit, f"HTTP {response.status_code}")
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # El scraping real de Indeed suele buscar elementos con clases específicas como 'resultContent'
        job_cards = soup.find_all(class_="resultContent")
        if not job_cards:
            # Si no encuentra elementos, es muy probable que haya saltado un captcha/bloqueo de Cloudflare
            return _mock_or_raise(keyword, provincia, modalidad, fuente, limit, "respuesta sin ofertas reconocibles")
            
        parsed_offers = []
        for card in job_cards[:limit]:
            try:
                # Estructura típica (simplificada para propósitos educativos)
                title_elem = card.find("span", id=lambda x: x and x.startswith("jobTitle"))
                company_elem = card.find("span", {"data-testid": "company-name"})
                location_elem = card.find("div", {"data-testid": "text-location"})
                
                titulo = title_elem.get_text(strip=True) if title_elem else "Desarrollador"
                empresa = company_elem.get_text(strip=True) if company_elem else "Empresa"
                ubicacion = location_elem.get_text(strip=True) if location_elem else "España"
                
                # Intentar buscar enlace
                link_elem = card.find("a")
                enlace = "https://es.indeed.com" + link_elem["href"] if link_elem and "href" in link_elem.attrs else indeed_url
                
                parsed_offers.append({
                    "titulo": titulo,
                    "empresa": empresa,
                    "ubicacion": ubicacion,
                    "modalidad": "Híbrido",  # Indeed no siempre lo tiene en un campo limpio, se asume Híbrido
                    "salario": "No especificado",
                    "descripcion": f"Oferta encontrada en Indeed para {titulo}.",
                    "enlace": enlace,
                    "fuente": fuente,
                    "estado": "guardado",
                    "fecha_publicacion": "Reciente"
                })
            except Exception:
                continue
                
        if not parsed_offers:
            return _mock_or_raise(keyword, provincia, modalidad, fuente, limit, "no se pudo interpretar ninguna oferta")
            
        return parsed_offers
        
    except Exception as e:
        logger.exception("Indeed connection failed: %s", e)
        if isinstance(e, RuntimeError):
            raise
        return _mock_or_raise(keyword, provincia, modalidad, fuente, limit, "error de conexión")


def fetch_indeed_offers(query: str = "python", limit: int = 10) -> List[Dict[str, Any]]:
    return search_indeed_offers(keyword=query, limit=limit)


def get_mock_indeed_offers(
    keyword: str = "python",
    provincia: str | None = None,
    modalidad: str | None = None,
    fuente: str = INDEED_SOURCE,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Devuelve ofertas mockeadas para simular Indeed España.
    """
    mock_data = [
        {
            "titulo": "Python Developer - IA & Data Science",
            "empresa": "AI Madrid Solutions",
            "ubicacion": "Madrid",
            "modalidad": "Remoto",
            "salario": "45.000€ - 55.000€ Bruto/Año",
            "descripcion": "Buscamos un Ingeniero de Software con experiencia sólida en Python, Pandas y modelos de lenguaje (LLMs).",
            "enlace": "https://es.indeed.com/viewjob?jk=indeed123456",
            "fuente": fuente,
            "estado": "guardado",
            "fecha_publicacion": "Hace 2 días"
        },
        {
            "titulo": "Programador Backend Python / Django",
            "empresa": "Digital Studio",
            "ubicacion": "Sevilla",
            "modalidad": "Híbrido",
            "salario": "28.000€ - 32.000€ Bruto/Año",
            "descripcion": "Desarrollo y mantenimiento de plataformas web robustas basadas en Django Framework y PostgreSQL.",
            "enlace": "https://es.indeed.com/viewjob?jk=indeed789012",
            "fuente": fuente,
            "estado": "guardado",
            "fecha_publicacion": "Hace 4 días"
        },
        {
            "titulo": "Senior Python Engineer",
            "empresa": "InnoTech Europe",
            "ubicacion": "Málaga",
            "modalidad": "Remoto",
            "salario": "55.000€ - 65.000€ Bruto/Año",
            "descripcion": "Buscamos un líder técnico que defina arquitectura de microservicios y optimice algoritmos complejos en Python.",
            "enlace": "https://es.indeed.com/viewjob?jk=indeed345678",
            "fuente": fuente,
            "estado": "guardado",
            "fecha_publicacion": "Hace 1 semana"
        }
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

    # Si la keyword no coincide con ninguno, devolvemos un fallback basado en la primera oferta mock
    if not filtered and keyword_value:
        filtered = [{**mock_data[0], "titulo": f"{mock_data[0]['titulo']} ({keyword})"}]
            
    return filtered[:limit]
