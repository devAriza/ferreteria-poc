"""
Motor combinado de recomendación.

Dado un producto ancla y una tienda, junta tres señales independientes ya
guardadas en `product_relations` (rules/llm, cooccurrence, manual), les
aplica un ajuste por clima de tienda, filtra por stock disponible, y regresa
el top-K con la explicación completa de por qué salió cada uno.

Por qué combinar en vez de elegir una sola señal:
- rules/llm capturan compatibilidad funcional que puede no tener respaldo
  en ventas todavía (catálogo nuevo, combinación rara).
- cooccurrence captura patrones reales de compra que ninguna regla
  anticiparía (ej. hábitos locales de una tienda en particular).
- manual es la última palabra del negocio: si alguien la marcó a mano,
  cuenta como señal fuerte incluso si las otras dos no la respaldan.

Ninguna señal por sí sola es "la respuesta correcta"; cada una cubre el
punto ciego de las otras dos.
"""
from collections import defaultdict

from sqlalchemy.orm import Session

from app.config import (
    WEIGHT_LLM_RULES, WEIGHT_COOCCURRENCE, WEIGHT_MANUAL_BOOST,
    CLIMATE_BOOST_FACTOR, CLIMATE_PENALTY_FACTOR, TOP_K_RECOMMENDATIONS,
)
from app.models import Product, ProductRelation, Store

WEATHER_RESISTANT_HINTS = ("inoxidable", "galvanizado", "ip65", "acrílico", "acrilico")
WEATHER_STANDARD_HINTS = ("estándar", "estandar", "acero al carbón", "acero al carbon")


def _climate_multiplier(material: str, clima: str) -> float:
    material_lower = material.lower()
    is_resistant = any(h in material_lower for h in WEATHER_RESISTANT_HINTS)
    is_standard = any(h in material_lower for h in WEATHER_STANDARD_HINTS)

    if clima == "costero":
        if is_resistant:
            return CLIMATE_BOOST_FACTOR
        if is_standard:
            return CLIMATE_PENALTY_FACTOR
    return 1.0


def get_recommendations(
    db: Session,
    product_id: str,
    tienda_id: str,
    top_k: int = TOP_K_RECOMMENDATIONS,
    allowed_sources: set[str] | None = None,
) -> list[dict]:
    """
    allowed_sources: si se pasa (ej. {"rules", "llm"} o {"cooccurrence"}),
    restringe qué señales participan en el score combinado. Se usa desde
    scripts/evaluate_recommendations.py para comparar el motor combinado
    contra cada señal aislada (ablation study), no se usa en producción.
    """
    anchor = db.query(Product).filter(Product.product_id == product_id).first()
    if anchor is None:
        raise ValueError(f"Producto {product_id} no existe")

    store = db.query(Store).filter(Store.tienda_id == tienda_id).first()
    if store is None:
        raise ValueError(f"Tienda {tienda_id} no existe")

    relations = (
        db.query(ProductRelation)
        .filter(
            ProductRelation.status == "active",
            (ProductRelation.product_a == product_id) | (ProductRelation.product_b == product_id),
        )
        .all()
    )

    # candidate_id -> source -> (score, explanation)   [nos quedamos con el mejor score por fuente]
    by_candidate: dict[str, dict[str, tuple[float, str]]] = defaultdict(dict)

    for rel in relations:
        if allowed_sources is not None and rel.source not in allowed_sources:
            continue
        other = rel.product_b if rel.product_a == product_id else rel.product_a
        if other == product_id:
            continue
        current = by_candidate[other].get(rel.source)
        if current is None or rel.score > current[0]:
            by_candidate[other][rel.source] = (rel.score, rel.explanation)

    candidate_ids = list(by_candidate.keys())
    if not candidate_ids:
        return []

    candidate_products = {
        p.product_id: p
        for p in db.query(Product).filter(Product.product_id.in_(candidate_ids)).all()
    }

    results = []
    for cid, sources in by_candidate.items():
        product = candidate_products.get(cid)
        if product is None or product.stock_disponible <= 0:
            continue  # regla dura: solo recomendar con existencia disponible

        # bucket "atributos": el mejor entre llm y rules (el LLM refina/reemplaza a rules)
        llm_score, llm_expl = sources.get("llm", (0.0, ""))
        rules_score, rules_expl = sources.get("rules", (0.0, ""))
        if llm_score >= rules_score:
            attr_score, attr_source, attr_expl = llm_score, "llm", llm_expl
        else:
            attr_score, attr_source, attr_expl = rules_score, "rules", rules_expl

        cooc_score, cooc_expl = sources.get("cooccurrence", (0.0, ""))
        manual_score, manual_expl = sources.get("manual", (0.0, ""))

        combined = (
            attr_score * WEIGHT_LLM_RULES
            + cooc_score * WEIGHT_COOCCURRENCE
            + manual_score * WEIGHT_MANUAL_BOOST
        )

        multiplier = _climate_multiplier(product.material, store.clima)
        combined *= multiplier

        reasons = []
        if attr_score > 0:
            label = "Inferido por IA (Gemini)" if attr_source == "llm" else "Regla de compatibilidad"
            reasons.append({"source": attr_source, "score": attr_score, "explanation": f"{label}: {attr_expl}"})
        if cooc_score > 0:
            reasons.append({"source": "cooccurrence", "score": cooc_score, "explanation": f"Historial de ventas: {cooc_expl}"})
        if manual_score > 0:
            reasons.append({"source": "manual", "score": manual_score, "explanation": f"Ajuste del negocio: {manual_expl}"})
        if multiplier != 1.0:
            clima_note = "priorizado" if multiplier > 1.0 else "des-priorizado"
            reasons.append({
                "source": "clima",
                "score": multiplier,
                "explanation": f"{clima_note} por clima de tienda ({store.clima})",
            })

        results.append({
            "product": product,
            "combined_score": round(combined, 4),
            "reasons": reasons,
        })

    results.sort(key=lambda r: r["combined_score"], reverse=True)
    return results[:top_k]
