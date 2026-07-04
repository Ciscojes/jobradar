from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.security import (
    create_access_token,
    hash_password,
    normalize_email,
    validate_email,
    verify_password,
)
from ..database import get_db
from ..deps import get_current_user
from ..services.scheduler import scan_single_alert


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


def _ensure_profile_alert(db: Session, user: models.User) -> None:
    """
    Si el usuario tiene un puesto deseado en su perfil, se asegura de que
    exista una alerta activa para ese puesto y la escanea al instante, para
    que ya tenga ofertas recomendadas nada mas entrar al dashboard.
    """
    if not user.puesto_deseado:
        return

    existing = (
        db.query(models.Alert)
        .filter(
            models.Alert.user_id == user.id,
            models.Alert.termino == user.puesto_deseado,
        )
        .first()
    )
    if existing:
        return

    alerta = models.Alert(
        user_id=user.id,
        termino=user.puesto_deseado,
        ubicacion=user.ubicacion_preferida or "Cualquiera",
        modalidad=user.modalidad_preferida or "Cualquiera",
        fuente="Adzuna",
        activo=True,
    )
    db.add(alerta)
    db.commit()
    db.refresh(alerta)

    try:
        scan_single_alert(db, alerta)
    except Exception as scan_error:
        print(f"Error al generar recomendaciones iniciales para {user.email}: {scan_error}")


@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    email = normalize_email(payload.email)
    if not validate_email(email):
        raise HTTPException(status_code=400, detail="Email inválido")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")

    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Ya existe un usuario con este email")

    user = models.User(
        email=email,
        nombre=payload.nombre,
        password_hash=hash_password(payload.password),
        puesto_deseado=payload.puesto_deseado,
        ubicacion_preferida=payload.ubicacion_preferida or "Cualquiera",
        modalidad_preferida=payload.modalidad_preferida or "Cualquiera",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Recomendaciones instantaneas: si ya dio un puesto deseado al registrarse,
    # generamos y escaneamos su alerta ya mismo.
    _ensure_profile_alert(db, user)

    return user


@router.post("/login", response_model=schemas.Token)
def login_user(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    email = normalize_email(payload.email)
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")

    return schemas.Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=schemas.User)
def read_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=schemas.User)
def update_me(
    payload: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)

    # Si acaba de completar/cambiar el puesto deseado, generamos recomendaciones ya.
    _ensure_profile_alert(db, current_user)

    return current_user
