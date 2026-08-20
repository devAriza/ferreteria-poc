"""
Motor de co-ocurrencia clásico (market basket) sobre `sales`, agrupado por
`ticket_id`. Usa lift, no conteo crudo:

    lift(A,B) = P(A,B) / (P(A) * P(B))

Un conteo crudo favorece productos que se venden mucho en general (tornillos,
cinta aislante) sin importar si de verdad están relacionados con el ancla.
Lift normaliza por qué tan frecuente es cada producto por separado, así que
resalta pares que se compran juntos MÁS de lo que la casualidad explicaría.

Esta señal es completamente independiente de la de rules_engine/llm_client:
no usa ningún atributo del catálogo, solo comportamiento de compra real. Por
eso se combina con las otras en vez de reemplazarlas (ver
recommendation_engine.py).
"""
from collections import defaultdict
from itertools import combinations

from sqlalchemy.orm import Session

from app.models import Sale


def _load_baskets(db: Session) -> list[set]:
    rows = db.query(Sale.ticket_id, Sale.product_id).all()
    baskets = defaultdict(set)
    for ticket_id, product_id in rows:
        baskets[ticket_id].add(product_id)
    return [b for b in baskets.values() if len(b) > 1]


def compute_cooccurrence_relations(db: Session, min_count: int = 3, min_lift: float = 1.1) -> list[dict]:
    """
    min_count: mínimo de canastas donde el par aparece junto, para evitar que
               una coincidencia aislada genere una relación "real".
    min_lift:  > 1 significa que se compran juntos más de lo esperado por azar.
               1.1 es un umbral conservador para un dataset de este tamaño.
    """
    baskets = _load_baskets(db)
    n_baskets = len(baskets)
    if n_baskets == 0:
        return []

    single_count = defaultdict(int)
    pair_count = defaultdict(int)

    for basket in baskets:
        for pid in basket:
            single_count[pid] += 1
        for a, b in combinations(sorted(basket), 2):
            pair_count[(a, b)] += 1

    relations = []
    for (a, b), count in pair_count.items():
        if count < min_count:
            continue
        p_a = single_count[a] / n_baskets
        p_b = single_count[b] / n_baskets
        p_ab = count / n_baskets
        lift = p_ab / (p_a * p_b) if p_a > 0 and p_b > 0 else 0

        if lift < min_lift:
            continue

        # Normalizamos lift a un score 0-1 con una función acotada
        # (lift de 1 -> 0, lift alto -> se acerca a 1 sin llegar).
        score = min(1.0, (lift - 1) / 4)

        relations.append({
            "product_a": a,
            "product_b": b,
            "score": round(score, 4),
            "explanation": f"comprados juntos en {count} tickets históricos (lift={lift:.2f})",
        })

    return relations
