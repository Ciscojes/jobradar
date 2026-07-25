import logging
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from typing import Dict, Any, Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import get_settings
from .database import engine, Base, get_db
from .deps import get_current_user
from .observability import configure_logging
from .rate_limit import limit_sync_attempts
from .routers import auth, ofertas, alertas, notificaciones, scheduler
from .services.manual_sync import enqueue_manual_sync
from .services.scheduler import ensure_scheduler_schema
from . import models, schemas

settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)

if settings.auto_create_tables:
    Base.metadata.create_all(bind=engine)
    ensure_scheduler_schema(engine)


app = FastAPI(
    title="jobradar API",
    description="API para centralizar ofertas de empleo y enviar alertas por Telegram.",
    version="1.0.0",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

# Configurar middleware de CORS para conectar con Streamlit u otros orígenes
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=list(settings.trusted_hosts),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    if settings.is_production:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


# Incluir los routers
app.include_router(auth.router)
app.include_router(ofertas.router)
app.include_router(alertas.router)
app.include_router(notificaciones.router)
app.include_router(scheduler.router)

@app.get("/")
def read_root() -> Dict[str, Any]:
    """
    Endpoint principal para verificar el estado de la API.
    """
    return {
        "status": "online",
        "message": "Bienvenido al Radar de Ofertas de Empleo Inteligente (jobradar)",
        "docs": "/docs" if settings.docs_enabled else None,
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "ok",
        "environment": settings.app_env,
    }

def offer_matches_alert(offer_data: Dict[str, Any], alert: models.Alerta) -> bool:
    """
    Comprueba si una oferta coincide con una alerta activa usando campos simples.
    Los valores "Cualquiera" actuan como comodines para ubicacion y modalidad.
    """
    if not alert.activo:
        return False

    searchable_text = " ".join(
        str(offer_data.get(field) or "")
        for field in ("titulo", "descripcion", "empresa")
    ).lower()
    if alert.termino.lower() not in searchable_text:
        return False

    alert_location = (alert.ubicacion or "Cualquiera").lower()
    offer_location = str(offer_data.get("ubicacion") or "").lower()
    if alert_location != "cualquiera" and alert_location not in offer_location:
        return False

    alert_modality = (alert.modalidad or "Cualquiera").lower()
    offer_modality = str(offer_data.get("modalidad") or "").lower()
    if alert_modality != "cualquiera" and alert_modality not in offer_modality:
        return False

    return True


def should_notify_offer(offer_data: Dict[str, Any], alerts: Iterable[models.Alerta]) -> bool:
    """Devuelve True si no hay alertas activas o si alguna alerta coincide."""
    active_alerts = [alert for alert in alerts if alert.activo]
    if not active_alerts:
        return True
    return any(offer_matches_alert(offer_data, alert) for alert in active_alerts)


def build_offer_notification(offer_data: Dict[str, Any]) -> str:
    return (
        f"🎯 *¡Nueva Oferta Encontrada!*\n\n"
        f"💼 *Puesto:* {offer_data.get('titulo')}\n"
        f"🏢 *Empresa:* {offer_data.get('empresa')}\n"
        f"📍 *Ubicación:* {offer_data.get('ubicacion')}\n"
        f"💼 *Modalidad:* {offer_data.get('modalidad')}\n"
        f"💰 *Salario:* {offer_data.get('salario')}\n"
        f"📡 *Fuente:* {offer_data.get('fuente')}\n\n"
        f"🔗 [Ver oferta]({offer_data.get('enlace')})"
    )


@app.post("/scraper/sync", status_code=200)
def sync_scraper(
    query: str = Query(
        "python",
        min_length=1,
        max_length=100,
        description="Término de búsqueda para sincronizar",
    ),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(limit_sync_attempts),
):
    """
    Encola una sincronización persistente para que la ejecute el worker.
    """
    job = enqueue_manual_sync(db, current_user.id, query)
    db.commit()
    return {
        "status": "queued",
        "job_id": job.id,
        "message": f"Sincronización para '{query}' encolada."
    }


@app.get("/scraper/runs", response_model=list[schemas.ScraperRun])
def read_scraper_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Historial de ejecuciones del scraper (manuales y del scheduler automático).
    """
    return (
        db.query(models.ScraperRun)
        .order_by(models.ScraperRun.started_at.desc(), models.ScraperRun.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
