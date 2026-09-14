from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional
from datetime import datetime


# --- schemas para Auth ---
class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    nombre: Optional[str] = Field(default=None, max_length=120)
    puesto_deseado: Optional[str] = Field(default=None, max_length=160)
    ubicacion_preferida: Optional[str] = Field(default="Cualquiera", max_length=160)
    modalidad_preferida: Optional[str] = Field(default="Cualquiera", max_length=80)


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


class User(BaseModel):
    id: int
    email: str
    nombre: Optional[str] = None
    is_active: bool
    created_at: datetime
    puesto_deseado: Optional[str] = None
    ubicacion_preferida: Optional[str] = None
    modalidad_preferida: Optional[str] = None
    nivel_experiencia: Optional[str] = None
    bio: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, max_length=120)
    puesto_deseado: Optional[str] = Field(default=None, max_length=160)
    ubicacion_preferida: Optional[str] = Field(default=None, max_length=160)
    modalidad_preferida: Optional[str] = Field(default=None, max_length=80)
    nivel_experiencia: Optional[str] = Field(default=None, max_length=80)
    bio: Optional[str] = Field(default=None, max_length=5_000)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- schemas para Ofertas ---
class OfertaBase(BaseModel):
    titulo: str = Field(min_length=1, max_length=300)
    empresa: str = Field(min_length=1, max_length=200)
    ubicacion: str = Field(min_length=1, max_length=200)
    modalidad: Optional[str] = Field(default="No especificado", max_length=80)
    salario: Optional[str] = Field(default="No especificado", max_length=120)
    descripcion: Optional[str] = Field(default=None, max_length=20_000)
    enlace: str = Field(min_length=1, max_length=2_048)
    fuente: str = Field(min_length=1, max_length=80)
    estado: Optional[Literal["guardado", "aplicado", "descartado"]] = "guardado"
    fecha_publicacion: Optional[str] = Field(default=None, max_length=40)

class OfertaCreate(OfertaBase):
    pass

class OfertaUpdateEstado(BaseModel):
    estado: Literal["guardado", "aplicado", "descartado"]

class Oferta(OfertaBase):
    id: int
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- schemas para Alertas ---
class AlertaBase(BaseModel):
    termino: str = Field(min_length=1, max_length=160)
    ubicacion: Optional[str] = Field(default="Cualquiera", max_length=160)
    categoria: Optional[str] = Field(default=None, max_length=120)
    salario_minimo: Optional[int] = Field(default=None, ge=0, le=100_000_000)
    modalidad: Optional[str] = Field(default="Cualquiera", max_length=80)
    fuente: Optional[str] = Field(default="Cualquiera", max_length=80)
    activo: Optional[bool] = True

class AlertaCreate(AlertaBase):
    pass


class AlertaUpdate(BaseModel):
    termino: Optional[str] = Field(default=None, min_length=1, max_length=160)
    ubicacion: Optional[str] = Field(default=None, max_length=160)
    categoria: Optional[str] = Field(default=None, max_length=120)
    salario_minimo: Optional[int] = Field(default=None, ge=0, le=100_000_000)
    modalidad: Optional[str] = Field(default=None, max_length=80)
    fuente: Optional[str] = Field(default=None, max_length=80)
    activo: Optional[bool] = None


class Alerta(AlertaBase):
    id: int
    user_id: int
    creado_en: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- schemas para Canales de notificacion ---
class NotificationChannelBase(BaseModel):
    type: str = Field(min_length=1, max_length=40)
    destination: str = Field(min_length=1, max_length=200)
    is_active: Optional[bool] = True


class NotificationChannelCreate(NotificationChannelBase):
    verification_token: Optional[str] = None


class NotificationChannelUpdate(BaseModel):
    type: Optional[str] = Field(default=None, min_length=1, max_length=40)
    destination: Optional[str] = Field(default=None, min_length=1, max_length=200)
    is_active: Optional[bool] = None
    verification_token: Optional[str] = Field(default=None, max_length=512)


class NotificationChannel(NotificationChannelBase):
    id: int
    user_id: int
    verified_at: Optional[datetime] = None
    created_at: datetime
    last_notification_status: Optional[str] = None
    last_notification_at: Optional[datetime] = None
    last_notification_error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationLog(BaseModel):
    id: int
    user_id: int
    alert_id: Optional[int] = None
    job_offer_id: Optional[int] = None
    user_oferta_id: Optional[int] = None
    channel_id: Optional[int] = None
    channel_type: Optional[str] = None
    destination: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScraperRun(BaseModel):
    id: int
    source: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_seconds: int = 0
    offers_found: int = 0
    new_offers: int = 0
    new_matches: int = 0
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
