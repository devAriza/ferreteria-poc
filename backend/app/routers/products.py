from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas import ProductOut, ProductCreate, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db), categoria: str | None = None, q: str | None = None):
    query = db.query(Product)
    if categoria:
        query = query.filter(Product.categoria == categoria)
    if q:
        like = f"%{q}%"
        query = query.filter(Product.nombre.ilike(like))
    return query.order_by(Product.nombre).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(404, f"Producto {product_id} no encontrado")
    return product


@router.post("", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.product_id == payload.product_id).first():
        raise HTTPException(409, f"Ya existe un producto con id {payload.product_id}")
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: str, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(404, f"Producto {product_id} no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(404, f"Producto {product_id} no encontrado")
    db.delete(product)
    db.commit()
    return None
