from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import get_settings
from .database import engine, Base, SessionLocal, get_db
from .deps import get_current_user
from .routers import auth, ofertas, alertas, notificaciones, scheduler
from .scraper.adzuna import fetch_adzuna_offers
from .scraper.indeed import fetch_indeed_offers
from .services.telegram import send_telegram_notification
from .services.scheduler import ensure_scheduler_schema, scheduler_service
from . import models, schemas

settings = get_settings()

if settings.auto_create_tables:
    Base.metadata.create_all(bind=engine)
    ensure_scheduler_schema(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_service.start()
    try:
        yield
    finally:
        scheduler_service.shutdown()


app = FastAPI(
    title="jobradar API",
    description="API para centralizar ofertas de empleo de Adzuna e Indeed y enviar alertas por Telegram.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

# Configurar middleware de CORS para conectar con Streamlit u otros orígenes
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def run_sync_task(query: str = "python") -> int:
    """
    Función auxiliar para ejecutar la sincronización en segundo plano.
    Trae ofertas de Adzuna e Indeed, las guarda en DB y notifica por Telegram si aplica.
    """
    db = SessionLocal()
    try:
        print(f"Iniciando sincronización para el término: '{query}'")
        adzuna_offers = fetch_adzuna_offers(query, limit=5)
        indeed_offers = fetch_indeed_offers(query, limit=5)

        all_offers = adzuna_offers + indeed_offers
        active_alerts = db.query(models.Alerta).filter(models.Alerta.activo.is_(True)).all()
        new_offers_count = 0

        for offer_data in all_offers:
            exists = db.query(models.Oferta).filter(models.Oferta.enlace == offer_data["enlace"]).first()
            if exists:
                continue

            db_offer = models.Oferta(**offer_data)
            db.add(db_offer)
            new_offers_count += 1

            if should_notify_offer(offer_data, active_alerts):
                try:
                    send_telegram_notification(build_offer_notification(offer_data))
                except Exception as telegram_error:
                    print(f"Error al enviar notificación a Telegram: {telegram_error}")

        db.commit()
        print(f"Sincronización terminada. Se han guardado {new_offers_count} nuevas ofertas.")
        return new_offers_count
    finally:
        db.close()

@app.post("/scraper/sync", status_code=200)
def sync_scraper(
    background_tasks: BackgroundTasks, 
    query: str = Query("python", description="Término de búsqueda para sincronizar"),
    current_user: models.User = Depends(get_current_user),
):
    """
    Sincronización manual que se ejecuta en segundo plano (Background Task)
    para evitar bloquear la respuesta HTTP.
    """
    background_tasks.add_task(run_sync_task, query)
    return {
        "status": "success",
        "message": f"Sincronización para '{query}' iniciada en segundo plano."
    }


@app.get("/scraper/runs", response_model=list[schemas.ScraperRun])
def read_scraper_runs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Historial de ejecuciones del scraper (manuales y del scheduler automático).
    """
    return (
        db.query(models.ScraperRun)
        .order_by(models.ScraperRun.started_at.desc(), models.ScraperRun.id.desc())
        .limit(limit)
        .all()
    )
