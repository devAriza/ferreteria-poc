"""
Evaluación de calidad de las recomendaciones: leave-one-out sobre canastas
reales de sales.csv.

Metodología
-----------
Para cada ticket histórico con 2+ productos distintos, y para cada producto
P dentro de esa canasta:
  1. Se pide al motor "qué recomendarías junto con P" (top-K), usando la
     tienda real del ticket.
  2. Se compara contra el resto de productos que el cliente SÍ se llevó en
     ese mismo ticket (el "ground truth" implícito).
  3. Se mide precision@k (de las K sugerencias, cuántas acertó) y recall@k
     (de lo que el cliente realmente compró junto, cuánto se recuperó).

Esto es una proxy, no la verdad absoluta: un cliente pudo no llevarse algo
que sí necesitaba (recall imperfecto por diseño), y el catálogo tiene
productos que rara vez se compran juntos aunque sean funcionalmente
compatibles (por eso el motor de reglas/LLM existe). Aun así, es la señal
más objetiva que tenemos con los datos disponibles, y sirve sobre todo para
comparar configuraciones ENTRE SÍ (combinado vs una sola señal), no para
juzgar el número en aislado.

Uso:
    python -m scripts.evaluate_recommendations
    python -m scripts.evaluate_recommendations --k 5 --sample 500
"""
import argparse
import random
from collections import defaultdict

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models import Sale
from app.services.recommendation_engine import get_recommendations


def _load_baskets_with_store(db):
    rows = db.query(Sale.ticket_id, Sale.product_id, Sale.tienda_id).all()
    baskets = defaultdict(set)
    store_of = {}
    for ticket_id, product_id, tienda_id in rows:
        baskets[ticket_id].add(product_id)
        store_of[ticket_id] = tienda_id
    return [
        (store_of[t], items) for t, items in baskets.items() if len(items) >= 2
    ]


def evaluate(db, k: int, sample: int | None, allowed_sources: set[str] | None, label: str):
    baskets = _load_baskets_with_store(db)
    if sample and sample < len(baskets):
        random.seed(7)
        baskets = random.sample(baskets, sample)

    precisions, recalls = [], []
    non_empty = 0
    total_eval = 0

    for tienda_id, items in baskets:
        items = list(items)
        for anchor in items:
            ground_truth = set(items) - {anchor}
            if not ground_truth:
                continue
            total_eval += 1
            try:
                recs = get_recommendations(db, anchor, tienda_id, top_k=k, allowed_sources=allowed_sources)
            except ValueError:
                continue
            if recs:
                non_empty += 1
            rec_ids = {r["product"].product_id for r in recs}
            hits = rec_ids & ground_truth

            precisions.append(len(hits) / k)
            recalls.append(len(hits) / len(ground_truth))

    n = len(precisions)
    avg_p = sum(precisions) / n if n else 0
    avg_r = sum(recalls) / n if n else 0
    coverage = non_empty / total_eval if total_eval else 0

    print(f"\n=== {label} (k={k}, n_evaluaciones={n}) ===")
    print(f"  precision@{k}: {avg_p:.4f}")
    print(f"  recall@{k}:    {avg_r:.4f}")
    print(f"  coverage:      {coverage:.2%}  (% de anclas con al menos 1 recomendación)")
    return {"precision": avg_p, "recall": avg_r, "coverage": coverage, "n": n}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--sample", type=int, default=800, help="Número de tickets a evaluar (None = todos)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print("Evaluando motor de recomendación con leave-one-out sobre canastas reales...")
        print("(comparando el motor combinado contra cada señal aislada)")

        results = {}
        results["combinado (rules+llm+cooccurrence+clima)"] = evaluate(
            db, args.k, args.sample, allowed_sources=None,
            label="COMBINADO (todas las señales)",
        )
        results["solo atributos (rules/llm)"] = evaluate(
            db, args.k, args.sample, allowed_sources={"rules", "llm"},
            label="SOLO ATRIBUTOS (rules + llm, sin ventas)",
        )
        results["solo co-ocurrencia"] = evaluate(
            db, args.k, args.sample, allowed_sources={"cooccurrence"},
            label="SOLO CO-OCURRENCIA (sin atributos)",
        )

        print("\n" + "=" * 60)
        print("RESUMEN COMPARATIVO")
        print("=" * 60)
        print(f"{'Configuración':<45}{'precision@k':<13}{'recall@k':<11}{'coverage'}")
        for name, r in results.items():
            print(f"{name:<45}{r['precision']:<13.4f}{r['recall']:<11.4f}{r['coverage']:.2%}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
