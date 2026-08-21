"""
Configuración centralizada. Todo lo que puede variar entre entornos vive
aquí y se lee de variables de entorno (ver .env.example en la raíz de backend/).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
PROJECT_ROOT = BASE_DIR.parent                       # ferreteria-poc/

load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/ferreteria.db")

DATA_DIR = os.getenv("DATA_DIR", str(PROJECT_ROOT / "data"))
PRODUCTS_CSV = os.path.join(DATA_DIR, "products.csv")
STORES_CSV = os.path.join(DATA_DIR, "stores.csv")
SALES_CSV = os.path.join(DATA_DIR, "sales.csv")

# --- LLM (Google Gemini) ---
# Se usa exclusivamente para el motor de extracción de relaciones funcionales
# (services/llm_client.py). Si GEMINI_API_KEY no está definida, el sistema sigue funcionando con reglas + co-ocurrencia (el LLM es un motor más, no una dependencia dura).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_API_URL = os.getenv(
    "GEMINI_API_URL",
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
)

# --- CORS ---
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

WEIGHT_LLM_RULES = float(os.getenv("WEIGHT_LLM_RULES", "0.45"))
WEIGHT_COOCCURRENCE = float(os.getenv("WEIGHT_COOCCURRENCE", "0.40"))
WEIGHT_MANUAL_BOOST = float(os.getenv("WEIGHT_MANUAL_BOOST", "0.15"))
CLIMATE_BOOST_FACTOR = float(os.getenv("CLIMATE_BOOST_FACTOR", "1.3"))
CLIMATE_PENALTY_FACTOR = float(os.getenv("CLIMATE_PENALTY_FACTOR", "0.6"))

TOP_K_RECOMMENDATIONS = int(os.getenv("TOP_K_RECOMMENDATIONS", "5"))
