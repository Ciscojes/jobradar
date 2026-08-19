import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship, synonym

from .database import Base


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    nombre = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    # Perfil profesional: se usa para generar automaticamente una alerta y
    # recomendar ofertas nada mas entrar, sin que el usuario tenga que crearla a mano.
    puesto_deseado = Column(String, nullable=True)
    ubicacion_preferida = Column(String, nullable=True, default="Cualquiera")
    modalidad_preferida = Column(String, nullable=True, default="Cualquiera")
    nivel_experiencia = Column(String, nullable=True)
    bio = Column(Text, nullable=True)

    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    notification_logs = relationship("NotificationLog", back_populates="user")
    notification_channels = relationship(
        "NotificationChannel", back_populates="user", cascade="all, delete-orphan"
    )
    user_ofertas = relationship("UserOferta", back_populates="user", cascade="all, delete-orphan")


class JobOffer(Base):
    __tablename__ = "ofertas"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    empresa = Column(String, nullable=False)
    ubicacion = Column(String, nullable=False)
    modalidad = Column(String, default="No especificado")
    salario = Column(String, default="No especificado")
    descripcion = Column(Text, nullable=True)
    enlace = Column(String, unique=True, index=True, nullable=False)
    fuente = Column(String, nullable=False)  # "Adzuna" or "Indeed"
    estado = Column(String, default="guardado")  # "guardado", "aplicado", "descartado"
    fecha_publicacion = Column(String, nullable=True)
    creado_en = Column(DateTime, default=utc_now)

    title = synonym("titulo")
    company = synonym("empresa")
    location = synonym("ubicacion")
    salary = synonym("salario")
    source = synonym("fuente")
    url = synonym("enlace")
    created_at = synonym("creado_en")

    notification_logs = relationship("NotificationLog", back_populates="job_offer")
    user_ofertas = relationship("UserOferta", back_populates="oferta", cascade="all, delete-orphan")


class Alert(Base):
    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    termino = Column(String, nullable=False)
    ubicacion = Column(String, default="Cualquiera")
    categoria = Column(String, nullable=True)
    salario_minimo = Column(Integer, nullable=True)
    modalidad = Column(String, default="Cualquiera")
    fuente = Column(String, default="Cualquiera")
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    keyword = synonym("termino")
    provincia = synonym("ubicacion")
    activa = synonym("activo")
    created_at = synonym("creado_en")

    user = relationship("User", back_populates="alerts")
    notification_logs = relationship("NotificationLog", back_populates="alert")
    user_ofertas = relationship("UserOferta", back_populates="alerta")


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # "telegram"
    destination = Column(String, nullable=False)  # chat_id
    is_active = Column(Boolean, default=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="notification_channels")
    notification_logs = relationship("NotificationLog", back_populates="channel_obj")


class UserOferta(Base):
    __tablename__ = "user_ofertas"
    __table_args__ = (
        UniqueConstraint("user_id", "oferta_id", name="uq_user_oferta"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    oferta_id = Column(Integer, ForeignKey("ofertas.id"), nullable=False, index=True)
    alerta_id = Column(Integer, ForeignKey("alertas.id"), nullable=True, index=True)
    estado = Column(String, default="guardado")  # "guardado", "aplicado", "descartado"
    matched_at = Column(DateTime, default=utc_now)
    notified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="user_ofertas")
    oferta = relationship("JobOffer", back_populates="user_ofertas")
    alerta = relationship("Alert", back_populates="user_ofertas")
    notification_logs = relationship("NotificationLog", back_populates="user_oferta")
    notification_outbox = relationship(
        "NotificationOutbox",
        back_populates="user_oferta",
        cascade="all, delete-orphan",
        uselist=False,
    )


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    id = Column(Integer, primary_key=True, index=True)
    user_oferta_id = Column(
        Integer,
        ForeignKey("user_ofertas.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    status = Column(String, nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    available_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    last_error = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    user_oferta = relationship("UserOferta", back_populates="notification_outbox")


class ManualSyncJob(Base):
    __tablename__ = "manual_sync_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    query = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    available_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)


class AlertScanJob(Base):
    __tablename__ = "alert_scan_jobs"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(
        Integer,
        ForeignKey("alertas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String, nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    available_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    dedupe_key = Column(String, nullable=True, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    __table_args__ = (
        UniqueConstraint("scope", "key_hash", "window_id", name="uq_rate_limit_bucket"),
    )

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    window_id = Column(Integer, nullable=False)
    request_count = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime, nullable=False, default=utc_now)


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id = Column(Integer, primary_key=True, index=True)
    worker_name = Column(String, nullable=False, unique=True, index=True)
    status = Column(String, nullable=False, default="starting")
    last_seen_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    last_error = Column(Text, nullable=True)
    manual_jobs_processed = Column(Integer, nullable=False, default=0)
    alert_jobs_processed = Column(Integer, nullable=False, default=0)
    notifications_processed = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=utc_now)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    alert_id = Column(Integer, ForeignKey("alertas.id"), nullable=True, index=True)
    job_offer_id = Column(Integer, ForeignKey("ofertas.id"), nullable=True, index=True)
    user_oferta_id = Column(Integer, ForeignKey("user_ofertas.id"), nullable=True, index=True)
    channel_id = Column(Integer, ForeignKey("notification_channels.id"), nullable=True, index=True)
    channel = Column(String, nullable=True)  # legacy: etiqueta libre de canal
    channel_type = Column(String, nullable=True)  # "telegram"
    destination = Column(String, nullable=True)
    status = Column(String, nullable=False)
    message = Column(Text, nullable=True)  # legacy: texto libre
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="notification_logs")
    alert = relationship("Alert", back_populates="notification_logs")
    job_offer = relationship("JobOffer", back_populates="notification_logs")
    user_oferta = relationship("UserOferta", back_populates="notification_logs")
    channel_obj = relationship("NotificationChannel", back_populates="notification_logs")


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, default=utc_now)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)
    offers_found = Column(Integer, default=0)
    new_offers = Column(Integer, default=0)
    new_matches = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)


Oferta = JobOffer
Alerta = Alert
