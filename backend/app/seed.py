"""
Carga inicial de datos: lee products.csv / stores.csv / sales.csv y puebla la
base. Después genera las relaciones base con rules_engine + cooccurrence
(siempre) y llm_client (solo si GEMINI_API_KEY está definida).

Se corre automáticamente al arrancar la app si la base está vacía (ver
main.py), y también se puede correr a mano:

    python -m app.seed              # carga completa (incluye LLM si hay key)
    python -m app.seed --no-llm     # fuerza a saltar el enriquecimiento LLM
"""
import argparse
import csv
import sys

from app.config import GEMINI_API_KEY, PRODUCTS_CSV, STORES_CSV, SALES_CSV
from app.database import SessionLocal, init_db
from app.models import Product, Store, Sale, ProductRelation
from app.services import rules_engine, cooccurrence


def _load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_base_data(db):
    if db.query(Store).count() > 0:
        print("[seed] stores ya cargadas, se omite")
    else:
        for row in _load_csv(STORES_CSV):
            db.add(Store(tienda_id=row["tienda_id"], nombre=row["nombre"], clima=row["clima"]))
        db.commit()
        print(f"[seed] stores cargadas")

    if db.query(Product).count() > 0:
        print("[seed] products ya cargados, se omite")
    else:
        for row in _load_csv(PRODUCTS_CSV):
            db.add(Product(
                product_id=row["product_id"],
                nombre=row["nombre"],
                categoria=row["categoria"],
                material=row["material"],
                uso_recomendado=row["uso_recomendado"],
                precio=float(row["precio"]),
                unidad=row["unidad"],
                stock_disponible=int(row["stock_disponible"]),
            ))
        db.commit()
        print(f"[seed] products cargados")

    if db.query(Sale).count() > 0:
        print("[seed] sales ya cargadas, se omite")
    else:
        rows = _load_csv(SALES_CSV)
        for row in rows:
            db.add(Sale(
                venta_id=row["venta_id"],
                ticket_id=row["ticket_id"],
                fecha=row["fecha"],
                tienda_id=row["tienda_id"],
                product_id=row["product_id"],
                cantidad=int(row["cantidad"]),
                precio_unitario=float(row["precio_unitario"]),
            ))
        db.commit()
        print(f"[seed] {len(rows)} filas de sales cargadas")


def generate_rule_relations(db):
    db.query(ProductRelation).filter(ProductRelation.source == "rules").delete()
    products = [
        {"product_id": p.product_id, "categoria": p.categoria, "material": p.material, "uso_recomendado": p.uso_recomendado}
        for p in db.query(Product).all()
    ]
    relations = rules_engine.generate_rule_relations(products)
    for r in relations:
        db.add(ProductRelation(
            product_a=r["product_a"], product_b=r["product_b"],
            source="rules", score=r["score"], explanation=r["explanation"],
            status="active",
        ))
    db.commit()
    print(f"[seed] {len(relations)} relaciones 'rules' generadas")


def generate_cooccurrence_relations(db):
    db.query(ProductRelation).filter(ProductRelation.source == "cooccurrence").delete()
    relations = cooccurrence.compute_cooccurrence_relations(db)
    for r in relations:
        db.add(ProductRelation(
            product_a=r["product_a"], product_b=r["product_b"],
            source="cooccurrence", score=r["score"], explanation=r["explanation"],
            status="active",
        ))
    db.commit()
    print(f"[seed] {len(relations)} relaciones 'cooccurrence' generadas")


def generate_llm_relations(db):
    if not GEMINI_API_KEY:
        print("[seed] GEMINI_API_KEY no configurada, se omite enriquecimiento LLM "
              "(el sistema sigue funcionando con rules + cooccurrence)")
        return

    from app.services import llm_client

    products = db.query(Product).all()
    by_category = {}
    for p in products:
        by_category.setdefault(p.categoria, []).append({
            "product_id": p.product_id, "categoria": p.categoria,
            "material": p.material, "uso_recomendado": p.uso_recomendado,
        })

    relations = llm_client.enrich_catalog_by_category(by_category)
    db.query(ProductRelation).filter(ProductRelation.source == "llm").delete()
    added = 0
    for r in relations:
        if r["product_a"] == r["product_b"]:
            continue
        db.add(ProductRelation(
            product_a=r["product_a"], product_b=r["product_b"],
            source="llm", score=r["score"], explanation=r["explanation"],
            status="active",
        ))
        added += 1
    db.commit()
    print(f"[seed] {added} relaciones 'llm' generadas")


def run(skip_llm: bool = False):
    init_db()
    db = SessionLocal()
    try:
        load_base_data(db)
        generate_rule_relations(db)
        generate_cooccurrence_relations(db)
        if not skip_llm:
            generate_llm_relations(db)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true", help="Omite el enriquecimiento vía Gemini")
    args = parser.parse_args()
    run(skip_llm=args.no_llm)
