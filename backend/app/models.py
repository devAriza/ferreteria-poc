"""
Modelo de datos.

Decisión clave: el inventario es UNA sola columna (`stock_disponible`) en
`products`, no una fila por tienda. Así se modela literalmente el enunciado
("bolsa compartida"): comprar desde cualquier tienda descuenta del mismo
lugar, y el control de sobreventa se hace con un UPDATE condicional atómico
(ver services/inventory_service.py), no con locks aplicativos.
"""
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, Text, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Store(Base):
    __tablename__ = "stores"

    tienda_id = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)
    clima = Column(String, nullable=False)  # 'costero' | 'interior'


class Product(Base):
    __tablename__ = "products"

    product_id = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    material = Column(String, nullable=False)
    uso_recomendado = Column(Text, nullable=False)
    precio = Column(Float, nullable=False)
    unidad = Column(String, nullable=False)
    stock_disponible = Column(Integer, nullable=False, default=0)


class Sale(Base):
    """
    Guarda tanto las ventas históricas cargadas de sales.csv como las nuevas
    compras hechas desde la UI (mismo esquema), para que el motor de
    co-ocurrencia siempre lea de una sola fuente de verdad que crece con uso
    real del sistema.
    """
    __tablename__ = "sales"

    venta_id = Column(String, primary_key=True)
    ticket_id = Column(String, nullable=False, index=True)
    fecha = Column(String, nullable=False)  # YYYY-MM-DD
    tienda_id = Column(String, ForeignKey("stores.tienda_id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.product_id"), nullable=False, index=True)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)


class ProductRelation(Base):
    """
    Relación dirigida producto_a -> producto_b ("si compran A, sugerir B"),
    con la fuente que la generó y un score normalizado 0-1 dentro de esa
    fuente. El motor combinado (recommendation_engine.py) las pondera y las
    junta; el admin las puede ver, editar o rechazar desde /admin/relations.

    source:
      - 'llm'          -> inferida por Gemini a partir de material/uso_recomendado
      - 'rules'        -> heurística de palabras clave (fallback sin API key)
      - 'cooccurrence' -> calculada de sales.csv (lift normalizado)
      - 'manual'       -> creada o editada a mano por el negocio

    status:
      - 'active'   -> se usa en las recomendaciones
      - 'rejected' -> el negocio la revisó y decidió que no aplica
    """
    __tablename__ = "product_relations"
    __table_args__ = (
        UniqueConstraint("product_a", "product_b", "source", name="uq_relation_source"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_a = Column(String, ForeignKey("products.product_id"), nullable=False, index=True)
    product_b = Column(String, ForeignKey("products.product_id"), nullable=False, index=True)
    source = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=False, default="")
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
