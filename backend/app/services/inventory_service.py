"""
Garantía de no-sobreventa.

El inventario es una sola bolsa compartida entre las 5 tiendas (una columna
`stock_disponible` por producto, no una fila por tienda). El riesgo es que
dos compras simultáneas desde tiendas distintas dejen el stock en negativo.

La solución NO es un lock en memoria de Python (no sirve si algún día corren
varios workers/procesos de uvicorn) sino delegar la atomicidad a la base de
datos: un solo UPDATE condicional que solo afecta una fila si hay stock
suficiente, dentro de una transacción. SQLite serializa escrituras a nivel de
archivo, así que esto es seguro incluso con requests concurrentes.

    UPDATE products
       SET stock_disponible = stock_disponible - :qty
     WHERE product_id = :pid AND stock_disponible >= :qty

Si `rowcount == 0`, no había stock suficiente y se aborta toda la venta
(todo o nada) antes de insertar cualquier fila en `sales`.
"""
import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Product


class InsufficientStockError(Exception):
    def __init__(self, product_id: str, disponible: int, solicitado: int):
        self.product_id = product_id
        self.disponible = disponible
        self.solicitado = solicitado
        super().__init__(
            f"Stock insuficiente para {product_id}: disponible={disponible}, solicitado={solicitado}"
        )


class ProductNotFoundError(Exception):
    pass


def _decrement_stock_atomic(db: Session, product_id: str, cantidad: int) -> int:
    """Devuelve el stock restante. Lanza InsufficientStockError si no alcanza."""
    result = db.execute(
        text(
            "UPDATE products SET stock_disponible = stock_disponible - :qty "
            "WHERE product_id = :pid AND stock_disponible >= :qty"
        ),
        {"qty": cantidad, "pid": product_id},
    )
    if result.rowcount == 0:
        product = db.query(Product).filter(Product.product_id == product_id).first()
        if product is None:
            raise ProductNotFoundError(f"Producto {product_id} no existe")
        raise InsufficientStockError(product_id, product.stock_disponible, cantidad)

    restante = db.query(Product.stock_disponible).filter(
        Product.product_id == product_id
    ).scalar()
    return restante


def execute_purchase(db: Session, tienda_id: str, items: list[dict]) -> dict:
    """
    items: [{"product_id": ..., "cantidad": ...}, ...]

    Todo-o-nada: si CUALQUIER item no tiene stock suficiente, se revierte la
    transacción completa (no se descuenta nada y no se registra la venta).
    """
    from app.models import Sale, Product as ProductModel  # local import evita ciclos

    ticket_id = f"T{uuid.uuid4().hex[:10].upper()}"
    fecha = date.today().isoformat()
    resultados = []
    total = 0.0

    try:
        for item in items:
            pid = item["product_id"]
            qty = item["cantidad"]

            product = db.query(ProductModel).filter(ProductModel.product_id == pid).first()
            if product is None:
                raise ProductNotFoundError(f"Producto {pid} no existe")
            precio_unitario = product.precio

            restante = _decrement_stock_atomic(db, pid, qty)

            venta_id = f"V{uuid.uuid4().hex[:10].upper()}"
            db.add(Sale(
                venta_id=venta_id,
                ticket_id=ticket_id,
                fecha=fecha,
                tienda_id=tienda_id,
                product_id=pid,
                cantidad=qty,
                precio_unitario=precio_unitario,
            ))
            resultados.append({
                "product_id": pid,
                "cantidad": qty,
                "precio_unitario": precio_unitario,
                "stock_restante": restante,
            })
            total += precio_unitario * qty

        db.commit()
    except (InsufficientStockError, ProductNotFoundError):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return {
        "ticket_id": ticket_id,
        "tienda_id": tienda_id,
        "fecha": fecha,
        "items": resultados,
        "total": total,
    }
