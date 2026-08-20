"""
Motor de reglas por atributos del catálogo.

Es la capa que SIEMPRE funciona, sin depender de ninguna API externa: infiere
compatibilidad funcional a partir de `categoria`, `material` y
`uso_recomendado` usando heurísticas deterministas. Sirve como:
  1. Fallback cuando no hay GEMINI_API_KEY configurada.
  2. Piso de calidad auditable: cualquier relación que el LLM proponga se
     puede comparar contra esta baseline simple.

No es Machine Learning: son reglas explícitas y legibles, a propósito, para
que el negocio pueda entender exactamente "por qué" salió cada sugerencia
sin depender de una caja negra.
"""
import itertools
import re
from collections import defaultdict

STOPWORDS = {
    "de", "en", "y", "para", "con", "la", "el", "los", "las", "un", "una",
    "a", "al", "del", "o", "su", "sus", "que", "por", "sin",
}

# Categorías que casi siempre se compran/instalan como parte del mismo
# proyecto, aunque el producto puntual no comparta material exacto.
PROJECT_CATEGORY_LINKS = {
    frozenset({"Plomería", "Construcción"}): 0.35,
    frozenset({"Plomería", "Herramientas"}): 0.25,
    frozenset({"Tornillería", "Herramientas"}): 0.30,
    frozenset({"Tornillería", "Herrajes"}): 0.35,
    frozenset({"Eléctrico", "Herramientas"}): 0.25,
    frozenset({"Pintura", "Herramientas"}): 0.35,
    frozenset({"Pintura", "Construcción"}): 0.30,
    frozenset({"Jardín", "Construcción"}): 0.20,
    frozenset({"Seguridad", "Herrajes"}): 0.25,
}

# Pares de material que indican una relación de uso conjunto directo
# (ej. algo se aplica sobre / se une con lo otro).
MATERIAL_COMPAT_KEYWORDS = [
    ("PVC", "PVC"),
    ("PTFE", "PVC"),
    ("Acrílico", "Vinil"),
    ("Solvente", "PVC"),
    ("Cemento", "Concreto"),
]


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-záéíóúñ0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _keyword_overlap_score(uso_a: str, uso_b: str) -> float:
    tokens_a = _tokenize(uso_a)
    tokens_b = _tokenize(uso_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    if not intersection:
        return 0.0
    return len(intersection) / len(union)  # Jaccard


def _material_link_score(mat_a: str, mat_b: str) -> float:
    for kw_a, kw_b in MATERIAL_COMPAT_KEYWORDS:
        has_a = kw_a.lower() in mat_a.lower()
        has_b = kw_b.lower() in mat_b.lower()
        has_b_in_a = kw_b.lower() in mat_a.lower()
        has_a_in_b = kw_a.lower() in mat_b.lower()
        if (has_a and has_b) or (has_b_in_a and has_a_in_b):
            return 0.4
    return 0.0


def _category_link_score(cat_a: str, cat_b: str) -> float:
    if cat_a == cat_b:
        return 0.15  # misma categoría: relación débil, ya se navega por catálogo
    return PROJECT_CATEGORY_LINKS.get(frozenset({cat_a, cat_b}), 0.0)


SUBSTITUTE_KW_THRESHOLD = 0.5


def _looks_like_substitute(product_a: dict, product_b: dict, kw_score: float) -> bool:
    """
    Detecta pares que son VARIANTES del mismo producto (mismo tubo en otro
    diámetro, mismo tornillo en otro material) en vez de complementos.

    Señal: texto de uso_recomendado casi idéntico + misma categoría. Esto
    importa porque en un catálogo real es más común tener texto de uso
    duplicado entre variantes que entre piezas que de verdad se instalan
    juntas (un tubo y su pegamento casi nunca comparten redacción). Sin este
    filtro, el motor de reglas termina recomendando "compra este mismo tubo
    en otra medida" en vez de "necesitas pegamento para instalarlo", que es
    justo el tipo de recomendación inútil que el negocio no quiere ver.
    """
    return kw_score >= SUBSTITUTE_KW_THRESHOLD and product_a["categoria"] == product_b["categoria"]


def score_pair(product_a: dict, product_b: dict) -> tuple[float, str]:
    """
    product_a / product_b: dicts con al menos categoria, material, uso_recomendado.
    Devuelve (score 0-1, explicación legible).
    """
    kw_score = _keyword_overlap_score(product_a["uso_recomendado"], product_b["uso_recomendado"])

    if _looks_like_substitute(product_a, product_b, kw_score):
        return 0.0, "descartado: parece ser una variante/sustituto del mismo producto, no un complemento"

    mat_score = _material_link_score(product_a["material"], product_b["material"])
    cat_score = _category_link_score(product_a["categoria"], product_b["categoria"])

    # Material pesa más que texto: dos productos que comparten redacción de
    # uso suelen ser sustitutos (ver filtro arriba); dos que comparten
    # familia de material (PVC+PVC, Solvente/PVC+PVC) suelen ser complementos.
    raw = kw_score * 0.25 + mat_score * 0.55 + cat_score * 0.20
    score = min(raw, 1.0)

    reasons = []
    if mat_score > 0:
        reasons.append(f"materiales compatibles ({product_a['material']} / {product_b['material']})")
    if kw_score > 0:
        reasons.append(f"uso relacionado ({kw_score:.0%} de palabras clave en común)")
    if cat_score > 0 and product_a["categoria"] != product_b["categoria"]:
        reasons.append(f"categorías que suelen combinarse en un mismo proyecto ({product_a['categoria']} + {product_b['categoria']})")
    elif cat_score > 0:
        reasons.append("misma categoría de producto")

    explanation = "; ".join(reasons) if reasons else "sin señal de compatibilidad relevante"
    return score, explanation


def generate_rule_relations(products: list[dict], min_score: float = 0.12) -> list[dict]:
    """
    Evalúa todos los pares de productos (excluyendo pares dentro del mismo
    grupo de variantes triviales, ej. mismo nombre con distinto material) y
    regresa las relaciones con score >= min_score.

    Para un catálogo de 55 productos son ~1,485 pares: trivial en costo.
    Con un catálogo real (miles de SKUs) esto se acotaría por categoría antes
    de comparar (ver README, sección "Cómo escalaría esto").
    """
    relations = []
    for a, b in itertools.combinations(products, 2):
        score, explanation = score_pair(a, b)
        if score >= min_score:
            relations.append({
                "product_a": a["product_id"],
                "product_b": b["product_id"],
                "score": round(score, 4),
                "explanation": explanation,
            })
    return relations
