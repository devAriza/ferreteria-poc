from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Store
from app.schemas import PurchaseRequest, PurchaseResponse
from app.services.inventory_service import (
    execute_purchase, InsufficientStockError, ProductNotFoundError,
)

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.post("", response_model=PurchaseResponse)
def create_purchase(payload: PurchaseRequest, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.tienda_id == payload.tienda_id).first()
    if not store:
        raise HTTPException(404, f"Tienda {payload.tienda_id} no encontrada")
    if not payload.items:
        raise HTTPException(400, "La compra debe incluir al menos un producto")

    try:
        result = execute_purchase(
            db, payload.tienda_id,
            [item.model_dump() for item in payload.items],
        )
    except ProductNotFoundError as e:
        raise HTTPException(404, str(e))
    except InsufficientStockError as e:
        raise HTTPException(
            409,
            f"Stock insuficiente para {e.product_id}: disponible={e.disponible}, "
            f"solicitado={e.solicitado}. La compra completa fue cancelada (todo o nada).",
        )

    return result
