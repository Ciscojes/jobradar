from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from .. import models, schemas
from ..deps import get_current_user

router = APIRouter(
    prefix="/ofertas",
    tags=["Ofertas"]
)

@router.get("/", response_model=List[schemas.Oferta])
def read_ofertas(
    q: Optional[str] = None,
    empresa: Optional[str] = None,
    ubicacion: Optional[str] = None,
    estado: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 100")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset debe ser mayor o igual que 0")

    query = db.query(models.Oferta)

    if isinstance(current_user, models.User):
        query = (
            query.join(models.UserOferta, models.UserOferta.oferta_id == models.Oferta.id)
            .filter(models.UserOferta.user_id == current_user.id)
        )
    
    if q:
        query = query.filter(
            (models.Oferta.titulo.ilike(f"%{q}%")) | 
            (models.Oferta.descripcion.ilike(f"%{q}%"))
        )
    if empresa:
        query = query.filter(models.Oferta.empresa.ilike(f"%{empresa}%"))
    if ubicacion:
        query = query.filter(models.Oferta.ubicacion.ilike(f"%{ubicacion}%"))
    if estado:
        query = query.filter(models.Oferta.estado == estado)

    return (
        query.order_by(models.Oferta.creado_en.desc(), models.Oferta.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

@router.get("/{oferta_id}", response_model=schemas.Oferta)
def read_oferta(
    oferta_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Oferta).filter(models.Oferta.id == oferta_id)
    if isinstance(current_user, models.User):
        query = (
            query.join(models.UserOferta, models.UserOferta.oferta_id == models.Oferta.id)
            .filter(models.UserOferta.user_id == current_user.id)
        )
    db_oferta = query.first()
    if not db_oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    return db_oferta

@router.post("/", response_model=schemas.Oferta, status_code=status.HTTP_201_CREATED)
def create_oferta(
    oferta: schemas.OfertaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Check if duplicate url
    db_existing = db.query(models.Oferta).filter(models.Oferta.enlace == oferta.enlace).first()
    if db_existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="La oferta con este enlace ya existe"
        )
    
    db_oferta = models.Oferta(**oferta.model_dump())
    db.add(db_oferta)
    db.flush()
    if isinstance(current_user, models.User):
        db.add(
            models.UserOferta(
                user_id=current_user.id,
                oferta_id=db_oferta.id,
                estado=db_oferta.estado,
            )
        )
    db.commit()
    db.refresh(db_oferta)
    return db_oferta

@router.patch("/{oferta_id}/estado", response_model=schemas.Oferta)
def update_oferta_estado(
    oferta_id: int, 
    estado_schema: schemas.OfertaUpdateEstado, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Oferta).filter(models.Oferta.id == oferta_id)
    user_oferta = None
    if isinstance(current_user, models.User):
        query = (
            query.join(models.UserOferta, models.UserOferta.oferta_id == models.Oferta.id)
            .filter(models.UserOferta.user_id == current_user.id)
        )
        user_oferta = (
            db.query(models.UserOferta)
            .filter(
                models.UserOferta.user_id == current_user.id,
                models.UserOferta.oferta_id == oferta_id,
            )
            .first()
        )

    db_oferta = query.first()
    if not db_oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    
    nuevo_estado = estado_schema.estado.lower()
    if nuevo_estado not in ["guardado", "aplicado", "descartado"]:
        raise HTTPException(
            status_code=400, 
            detail="Estado inválido. Debe ser 'guardado', 'aplicado' o 'descartado'"
        )
        
    db_oferta.estado = nuevo_estado
    if user_oferta is not None:
        user_oferta.estado = nuevo_estado
    db.commit()
    db.refresh(db_oferta)
    return db_oferta
