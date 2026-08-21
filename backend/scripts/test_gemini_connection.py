"""
Diagnóstico aislado de la conexión a Gemini

Uso:
    cd backend
    python -m scripts.test_gemini_connection para pruebas de LLM
"""
import sys
import os
from app.config import GEMINI_API_KEY, GEMINI_API_URL, GEMINI_MODEL
from app.services.llm_client import call_gemini_for_relations
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


TEST_PRODUCTS = [
    {"product_id": "P001", "categoria": "Plomería", "material": "PVC",
     "uso_recomendado": "Conducción de agua fría, instalaciones domésticas"},
    {"product_id": "P005", "categoria": "Plomería", "material": "Solvente/PVC",
     "uso_recomendado": "Sellado y unión permanente de tubería PVC"},
    {"product_id": "P006", "categoria": "Plomería", "material": "PTFE",
     "uso_recomendado": "Sellado de roscas en conexiones de agua y gas"},
    {"product_id": "P100", "categoria": "Herramientas", "material": "Metal/plástico ABS",
     "uso_recomendado": "Perforación en concreto, madera y metal"},
]

def main():
    print(f"Modelo: {GEMINI_MODEL}")
    print(f"URL:    {GEMINI_API_URL}")
    print(f"Key configurada: {'sí (' + GEMINI_API_KEY[:6] + '...)' if GEMINI_API_KEY else 'NO -- falta en backend/.env'}")
    print()

    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY no está definida. Revisa backend/.env (no config.py).")
        sys.exit(1)

    print(f"Enviando {len(TEST_PRODUCTS)} productos de prueba a Gemini...")
    try:
        relations = call_gemini_for_relations(TEST_PRODUCTS)
    except Exception as e:
        print(f"La llamada falló: {type(e).__name__}: {e}")
        print("\nCausas comunes:")
        print("s - Key inválida o sin habilitar en https://aistudio.google.com/apikey")
        print("s - GEMINI_MODEL con nombre incorrecto (revisa modelos disponibles en tu cuenta)")
        print("s - Cuota gratuita agotada (rate limit) -- espera un minuto y reintenta")
        sys.exit(1)

    if not relations:
        print("La llamada tuvo éxito pero Gemini no devolvió ninguna relación.")
        print("Puede pasar si el modelo decidió que ningún par amerita relación")
        print("fuerte con solo 4 productos de prueba. No es necesariamente un error.")
        sys.exit(0)

    print(f"Gemini respondió con {len(relations)} relación(es):\n")
    for r in relations:
        print(f"  {r['product_a']} -> {r['product_b']}  (score={r['score']:.2f})")
        print(f"      {r['explanation']}")

    expected_pair = {"P001", "P005"}
    found = any({r["product_a"], r["product_b"]} == expected_pair for r in relations)
    print()
    if found:
        print("Encontró la relación esperada tubo PVC (P001) <-> pegamento PVC (P005).")
        print("   La integración está funcionando end-to-end.")
    else:
        print("No encontró específicamente P001<->P005, pero la llamada sí funcionó.")
        print("   Revisa las relaciones de arriba -- puede que haya encontrado otras válidas.")


if __name__ == "__main__":
    main()
