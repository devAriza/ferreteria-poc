from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Store
from app.schemas import StoreOut

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("", response_model=list[StoreOut])
def list_stores(db: Session = Depends(get_db)):
    return db.query(Store).order_by(Store.nombre).all()
