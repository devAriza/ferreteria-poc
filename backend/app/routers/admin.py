from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProductRelation
from app.schemas import RelationOut, RelationCreate, RelationStatusUpdate

router = APIRouter(prefix="/admin/relations", tags=["admin"])


@router.get("", response_model=list[RelationOut])
def list_relations(
    db: Session = Depends(get_db),
    product_id: str | None = None,
    source: str | None = None,
    status: str | None = None,
):
    """
    Vista para que el negocio audite qué relaciones está encontrando el
    sistema, de dónde salió cada una (llm/rules/cooccurrence/manual) y con
    qué score, y las pueda filtrar por producto/fuente/estado.
    """
    query = db.query(ProductRelation)
    if product_id:
        query = query.filter(
            (ProductRelation.product_a == product_id) | (ProductRelation.product_b == product_id)
        )
    if source:
        query = query.filter(ProductRelation.source == source)
    if status:
        query = query.filter(ProductRelation.status == status)
    return query.order_by(ProductRelation.score.desc()).all()


@router.post("", response_model=RelationOut, status_code=201)
def create_manual_relation(payload: RelationCreate, db: Session = Depends(get_db)):
    """El negocio fuerza una relación que el sistema no detectó."""
    existing = db.query(ProductRelation).filter(
        ProductRelation.product_a == payload.product_a,
        ProductRelation.product_b == payload.product_b,
        ProductRelation.source == "manual",
    ).first()
    if existing:
        raise HTTPException(409, "Ya existe una relación manual para este par")

    relation = ProductRelation(
        product_a=payload.product_a,
        product_b=payload.product_b,
        source="manual",
        score=payload.score,
        explanation=payload.explanation,
        status="active",
    )
    db.add(relation)
    db.commit()
    db.refresh(relation)
    return relation


@router.patch("/{relation_id}", response_model=RelationOut)
def update_relation_status(relation_id: int, payload: RelationStatusUpdate, db: Session = Depends(get_db)):
    """El negocio acepta o rechaza una relación sugerida por rules/llm/cooccurrence."""
    if payload.status not in ("active", "rejected"):
        raise HTTPException(400, "status debe ser 'active' o 'rejected'")
    relation = db.query(ProductRelation).filter(ProductRelation.id == relation_id).first()
    if not relation:
        raise HTTPException(404, "Relación no encontrada")
    relation.status = payload.status
    db.commit()
    db.refresh(relation)
    return relation


@router.delete("/{relation_id}", status_code=204)
def delete_relation(relation_id: int, db: Session = Depends(get_db)):
    relation = db.query(ProductRelation).filter(ProductRelation.id == relation_id).first()
    if not relation:
        raise HTTPException(404, "Relación no encontrada")
    db.delete(relation)
    db.commit()
    return None
