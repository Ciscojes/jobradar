from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..services.scheduler import get_scheduler_status


router = APIRouter(
    prefix="/scheduler",
    tags=["Scheduler"],
)


@router.get("/status")
def read_scheduler_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    return get_scheduler_status(db)
