"""
Motor de extracción de relaciones vía LLM (Google Gemini, API gratuita).

Este es el bloque que resuelve lo que el brief señala como el punto ciego
de cualquier motor puramente estadístico: relaciones funcionales que casi
no aparecen en el historial de ventas (ej. tubo + pegamento PVC, con solo
1.5% de co-ocurrencia real en nuestro dataset a pesar de que uno siempre
necesita al otro) y contexto ambiental (clima costero vs interior) que no
está en `sales.csv` en absoluto.

Diseño:
- Se le manda al modelo el catálogo (o un subconjunto por categoría, para no
  saturar el contexto) con product_id, categoria, material, uso_recomendado.
- Se le pide EXCLUSIVAMENTE JSON: lista de {product_a, product_b, score,
  explicacion}. Nada de texto libre alrededor, para poder parsear sin
  ambigüedad.
- El resultado se cachea en la tabla `product_relations` con source='llm',
  para no volver a llamar a la API en cada request de recomendación
  (llamar al LLM es un paso de "enriquecimiento offline" del catálogo, no
  algo que corre en el hot path de una recomendación individual).

IMPORTANTE (transparencia sobre el estado de esto en la entrega):
No pude ejecutar llamadas reales a la API de Gemini desde el sandbox donde
construí este proyecto (su red de salida solo permite pypi/npm/github/
api.anthropic.com). El código de este archivo está completo y lo puedes
probar en tu máquina con tu propia GEMINI_API_KEY (ver backend/.env.example
y README.md). Si GEMINI_API_KEY no está configurada, `enrich_catalog_with_llm`
simplemente no hace nada y el sistema sigue funcionando con rules_engine +
cooccurrence (degradación explícita, no falla silenciosa a medias).
"""
import json
import re

import httpx

from app.config import GEMINI_API_KEY, GEMINI_API_URL

SYSTEM_INSTRUCTIONS = """Eres un experto ferretero con 20 años de experiencia en piso de venta.
Tu trabajo es identificar qué productos se necesitan juntos para completar un proyecto o
reparación típica, basándote en su material y uso recomendado - NO en si históricamente se
han vendido juntos (eso ya lo calculamos aparte).

Presta especial atención a:
1. Compatibilidad de material (ej. un pegamento PVC solo sirve con tubería PVC, no con cobre).
2. Insumos que un producto SIEMPRE requiere para instalarse o usarse por completo, aunque el
   cliente no los pida explícitamente (ej. una llave de paso necesita cinta teflón para sellar).
3. Contexto ambiental: si un producto es para exteriores o zonas húmedas/costeras, prioriza
   relacionarlo con variantes resistentes a corrosión (galvanizado, inoxidable, IP65) en vez
   de las versiones estándar.

Responde ÚNICAMENTE con un array JSON, sin texto antes ni después, sin markdown:
[
  {"product_a": "P001", "product_b": "P005", "score": 0.9, "explicacion": "..."},
  ...
]
- score entre 0 y 1 (qué tan indispensable/relevante es la relación).
- explicacion en español, una frase corta y concreta (máx 15 palabras).
- Solo incluye pares que un vendedor experto realmente sugeriría. No fuerces relaciones débiles.
"""


def _build_user_prompt(products: list[dict]) -> str:
    catalog_lines = [
        f"{p['product_id']} | {p['categoria']} | {p['material']} | {p['uso_recomendado']}"
        for p in products
    ]
    return (
        "Catálogo (product_id | categoria | material | uso_recomendado):\n"
        + "\n".join(catalog_lines)
        + "\n\nDevuelve el array JSON de relaciones producto_a -> producto_b."
    )


def _extract_json_array(text: str) -> list:
    """Gemini a veces envuelve la respuesta en ```json ... ``` a pesar de la instrucción.
    Esto la limpia antes de parsear."""
    cleaned = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No se encontró un array JSON en la respuesta del LLM: {text[:200]}")
    return json.loads(match.group(0))


def call_gemini_for_relations(products: list[dict], timeout: float = 60.0) -> list[dict]:
    """
    products: lista de dicts con product_id, categoria, material, uso_recomendado.
    Devuelve: [{"product_a", "product_b", "score", "explanation"}, ...]

    Lanza RuntimeError si GEMINI_API_KEY no está configurada, o la excepción
    original de httpx si la llamada falla (se deja propagar a propósito para
    que el caller decida cómo loggearlo, en vez de tragarse el error).
    """
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY no está configurada. Define la variable de entorno "
            "para habilitar el motor de relaciones por LLM (ver .env.example)."
        )

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTIONS}]},
        "contents": [{"role": "user", "parts": [{"text": _build_user_prompt(products)}]}],
        "generationConfig": {
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            GEMINI_API_URL,
            params={"key": GEMINI_API_KEY},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    raw_relations = _extract_json_array(text)

    relations = []
    for r in raw_relations:
        try:
            relations.append({
                "product_a": r["product_a"],
                "product_b": r["product_b"],
                "score": max(0.0, min(1.0, float(r["score"]))),
                "explanation": r.get("explicacion") or r.get("explanation") or "",
            })
        except (KeyError, ValueError, TypeError):
            continue  # ignora entradas mal formadas en vez de tumbar todo el batch

    return relations


def enrich_catalog_by_category(products_by_category: dict[str, list[dict]]) -> list[dict]:
    """
    Llama a Gemini una vez POR CATEGORÍA en vez de mandar las 55+ filas del
    catálogo en un solo prompt. Con un catálogo real de miles de SKUs esto es
    obligatorio por límite de contexto y de costo; aquí con 55 productos ya
    se hace así desde el inicio para que el patrón escale sin refactor.

    Además, cruza cada categoría con las 2 categorías más relacionadas
    (ver rules_engine.PROJECT_CATEGORY_LINKS) para no perder relaciones
    inter-categoría como "tubo (Plomería) + llave inglesa (Herramientas)".
    """
    from app.services.rules_engine import PROJECT_CATEGORY_LINKS

    all_relations = []
    categories = list(products_by_category.keys())

    for cat in categories:
        related_cats = {cat}
        for pair, _ in PROJECT_CATEGORY_LINKS.items():
            if cat in pair:
                related_cats |= set(pair)

        batch = []
        for c in related_cats:
            batch.extend(products_by_category.get(c, []))

        if len(batch) < 2:
            continue

        try:
            relations = call_gemini_for_relations(batch)
            all_relations.extend(relations)
        except Exception as e:
            # No tumbamos todo el enriquecimiento si UNA categoría falla
            # (rate limit, timeout, etc.) - se loggea y se sigue.
            print(f"[llm_client] Aviso: falló enriquecimiento de categoría '{cat}': {e}")
            continue

    return all_relations
