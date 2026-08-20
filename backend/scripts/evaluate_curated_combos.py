"""
Evaluación complementaria a evaluate_recommendations.py.

El leave-one-out sobre sales.csv mide contra el propio historial de ventas,
así que estructuralmente premia a la señal de co-ocurrencia y no puede
validar la razón de ser del motor de atributos (rules/llm): relaciones
funcionales que casi no aparecen en las ventas todavía.

Este script usa un set de referencia definido por criterio de negocio (yo,
haciendo de "experto ferretero" al diseñar data/generate_data.py) con dos
grupos:

  - STRONG:  combos de alta rotación, SÍ deberían aparecer en co-ocurrencia.
  - WEAK:    combos funcionalmente obligatorios pero de bajo respaldo en
             ventas (< 2% co-ocurrencia real, ver validación de datos).

La hipótesis a probar: co-ocurrencia acierta en STRONG y falla en WEAK;
rules/llm acierta en ambos. Si eso se confirma, es la evidencia de que
combinar señales no es cosmético, es necesario.

Uso:
    python -m scripts.evaluate_curated_combos
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.services.recommendation_engine import get_recommendations

# Mismos combos que data/generate_data.py (duplicados aquí a propósito: ese
# archivo define cómo se generaron las VENTAS, este define qué es "correcto"
# desde el punto de vista funcional/negocio - son dos fuentes de verdad
# distintas y así debe ser).
STRONG_COMBOS = [
    ("P020", "P023"), ("P021", "P023"), ("P022", "P023"),
    ("P041", "P043"), ("P042", "P043"),
    ("P063", "P060"), ("P064", "P061"),
    ("P100", "P101"), ("P100", "P102"),
]

WEAK_BUT_LOGICAL_COMBOS = [
    ("P001", "P005"), ("P001", "P006"), ("P002", "P005"),
    ("P007", "P006"), ("P012", "P013"), ("P062", "P060"),
    ("P080", "P082"), ("P085", "P024"),
]

STORE_FOR_TEST = "CDMX"  # tienda de interior, neutral para no mezclar con el efecto clima
K = 8  # top-k generoso: lo que nos interesa es si la relación aparece, no la posición exacta


def hit_rate(db, combos, allowed_sources, label):
    hits = 0
    details = []
    for a, b in combos:
        try:
            recs = get_recommendations(db, a, STORE_FOR_TEST, top_k=K, allowed_sources=allowed_sources)
        except ValueError:
            continue
        rec_ids = {r["product"].product_id for r in recs}
        hit = b in rec_ids
        hits += hit
        details.append((a, b, hit))

    rate = hits / len(combos) if combos else 0
    print(f"  [{label}] hit@{K}: {hits}/{len(combos)} = {rate:.0%}")
    for a, b, hit in details:
        mark = "✓" if hit else "✗"
        print(f"      {mark} {a} -> {b}")
    return rate


def main():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("COMBOS FUERTES (alta rotación histórica, ~66% co-ocurrencia real)")
        print("=" * 70)
        hit_rate(db, STRONG_COMBOS, {"cooccurrence"}, "solo co-ocurrencia")
        hit_rate(db, STRONG_COMBOS, {"rules", "llm"}, "solo atributos (rules/llm)")
        hit_rate(db, STRONG_COMBOS, None, "combinado")

        print()
        print("=" * 70)
        print("COMBOS LÓGICOS RAROS EN VENTA (~1.5% co-ocurrencia real)")
        print("=" * 70)
        hit_rate(db, WEAK_BUT_LOGICAL_COMBOS, {"cooccurrence"}, "solo co-ocurrencia")
        hit_rate(db, WEAK_BUT_LOGICAL_COMBOS, {"rules", "llm"}, "solo atributos (rules/llm)")
        hit_rate(db, WEAK_BUT_LOGICAL_COMBOS, None, "combinado")

        print()
        print("Conclusión esperada: co-ocurrencia debería fallar en el segundo bloque")
        print("(son combos que casi no están en el historial) y rules/llm debería")
        print("sostenerlos en ambos, justificando por qué el motor los combina.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
