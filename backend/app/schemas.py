from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ---------- Store ----------
class StoreOut(BaseModel):
    tienda_id: str
    nombre: str
    clima: str

    class Config:
        from_attributes = True


# ---------- Product ----------
class ProductBase(BaseModel):
    nombre: str
    categoria: str
    material: str
    uso_recomendado: str
    precio: float = Field(gt=0)
    unidad: str
    stock_disponible: int = Field(ge=0)


class ProductCreate(ProductBase):
    product_id: str


class ProductUpdate(BaseModel):
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    material: Optional[str] = None
    uso_recomendado: Optional[str] = None
    precio: Optional[float] = Field(default=None, gt=0)
    unidad: Optional[str] = None
    stock_disponible: Optional[int] = Field(default=None, ge=0)


class ProductOut(ProductBase):
    product_id: str

    class Config:
        from_attributes = True


# ---------- Purchase / Sale ----------
class PurchaseItem(BaseModel):
    product_id: str
    cantidad: int = Field(gt=0)


class PurchaseRequest(BaseModel):
    tienda_id: str
    items: List[PurchaseItem]


class PurchaseResultItem(BaseModel):
    product_id: str
    cantidad: int
    precio_unitario: float
    stock_restante: int


class PurchaseResponse(BaseModel):
    ticket_id: str
    tienda_id: str
    fecha: str
    items: List[PurchaseResultItem]
    total: float


# ---------- Recommendations ----------
class RecommendationExplanation(BaseModel):
    source: str
    score: float
    explanation: str


class RecommendationOut(BaseModel):
    product: ProductOut
    combined_score: float
    reasons: List[RecommendationExplanation]


# ---------- Relations (admin) ----------
class RelationOut(BaseModel):
    id: int
    product_a: str
    product_b: str
    source: str
    score: float
    explanation: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RelationCreate(BaseModel):
    product_a: str
    product_b: str
    score: float = Field(ge=0, le=1, default=1.0)
    explanation: str = "Relación creada manualmente por el negocio"


class RelationStatusUpdate(BaseModel):
    status: str  # 'active' | 'rejected'
