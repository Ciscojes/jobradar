import logging
import re
import time
import uuid
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from typing import Dict, Any, Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .config import get_settings
from .database import engine, Base, get_db
from .deps import get_current_user
from .observability import configure_logging, request_id_context
from .rate_limit import limit_sync_attempts
from .routers import auth, ofertas, alertas, notificaciones, scheduler
from .services.manual_sync import enqueue_manual_sync
from .services.ingestion import offer_matches_alert as _offer_matches_alert
from .services.scheduler import ensure_scheduler_schema
from . import models, schemas

settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)

HTTP_REQUESTS = Counter(
    "jobradar_http_requests_total",
    "Peticiones HTTP recibidas",
    ("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "jobradar_http_request_duration_seconds",
    "Duración de peticiones HTTP",
    ("method", "route"),
)

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
    supplied_request_id = request.headers.get("x-request-id", "")
    request_id = (
        supplied_request_id
        if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_request_id)
        else uuid.uuid4().hex
    )
    token = request_id_context.set(request_id)
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        route = getattr(request.scope.get("route"), "path", request.url.path)
        HTTP_REQUESTS.labels(request.method, route, "500").inc()
        HTTP_DURATION.labels(request.method, route).observe(time.perf_counter() - started_at)
        logger.exception(
            "request_failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
        )
        request_id_context.reset(token)
        raise

    response.headers["X-Request-ID"] = request_id
    route = getattr(request.scope.get("route"), "path", request.url.path)
    HTTP_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
    HTTP_DURATION.labels(request.method, route).observe(time.perf_counter() - started_at)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    if settings.is_production:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    logger.info(
        "request_completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
        },
    )
    request_id_context.reset(token)
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


@app.get("/health/live")
def liveness_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    health_check(db)
    heartbeat = (
        db.query(models.WorkerHeartbeat)
        .filter(models.WorkerHeartbeat.worker_name == "scheduler")
        .first()
    )
    if heartbeat is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El worker todavía no ha reportado estado",
        )
    current_time = models.utc_now()
    if heartbeat.last_seen_at.tzinfo is None:
        current_time = current_time.replace(tzinfo=None)
    age_seconds = (current_time - heartbeat.last_seen_at).total_seconds()
    if heartbeat.status == "error" or age_seconds > 180:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El worker no está disponible",
        )
    return {"status": "ok", "database": "ok", "worker": "ok"}


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics(authorization: str | None = Header(default=None)) -> Response:
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Métricas desactivadas")
    if settings.metrics_token and authorization != f"Bearer {settings.metrics_token}":
        raise HTTPException(status_code=401, detail="Token de métricas inválido")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

def offer_matches_alert(offer_data: Dict[str, Any], alert: models.Alerta) -> bool:
    return _offer_matches_alert(offer_data, alert)


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
        .filter(models.ScraperRun.user_id == current_user.id)
        .order_by(models.ScraperRun.started_at.desc(), models.ScraperRun.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
