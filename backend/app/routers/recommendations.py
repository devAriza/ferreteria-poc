from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import RecommendationOut
from app.services.recommendation_engine import get_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationOut])
def recommend(
    product_id: str = Query(..., description="Producto ancla, ej. P001"),
    tienda_id: str = Query(..., description="Tienda desde la que se está comprando"),
    top_k: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    try:
        results = get_recommendations(db, product_id, tienda_id, top_k)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return results
