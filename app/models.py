<<<<<<< HEAD
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Oferta(Base):
    __tablename__ = "ofertas"

    id            = Column(Integer, primary_key=True, index=True)
    titulo        = Column(String, nullable=False)
    empresa       = Column(String)
    ciudad        = Column(String)
    modalidad     = Column(String)           # remoto / presencial / hibrido
    salario       = Column(String)
    tecnologias   = Column(String)           # guardado como string separado por comas
    url           = Column(String, unique=True)
    estado        = Column(String, default="sin_revisar")  # sin_revisar / aplicado / guardado / descartado
    fecha_pub     = Column(String)
    creado_en     = Column(DateTime, server_default=func.now())


class Alerta(Base):
    __tablename__ = "alertas"

    id        = Column(Integer, primary_key=True, index=True)
    keyword   = Column(String, nullable=False)
    ciudad    = Column(String)
    modalidad = Column(String)
    activa    = Column(Boolean, default=True)
    creado_en = Column(DateTime, server_default=func.now())
=======
import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
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

    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    notification_logs = relationship("NotificationLog", back_populates="user")


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
    fuente = Column(String, nullable=False)  # "InfoJobs" or "Indeed"
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


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    alert_id = Column(Integer, ForeignKey("alertas.id"), nullable=True, index=True)
    job_offer_id = Column(Integer, ForeignKey("ofertas.id"), nullable=True, index=True)
    channel = Column(String, nullable=False)
    status = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="notification_logs")
    alert = relationship("Alert", back_populates="notification_logs")
    job_offer = relationship("JobOffer", back_populates="notification_logs")


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
    error_message = Column(Text, nullable=True)


Oferta = JobOffer
Alerta = Alert
>>>>>>> cisco/main
