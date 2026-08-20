from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import FRONTEND_ORIGIN
from app.database import init_db, SessionLocal
from app.models import Product
from app.routers import products, stores, sales, recommendations, admin

app = FastAPI(
    title="Ferretería POC - Inventario y Recomendaciones",
    description=(
        "POC de un sistema de inventario compartido multi-tienda con motor "
        "de recomendación híbrido (reglas/LLM + co-ocurrencia + clima)."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(stores.router)
app.include_router(sales.router)
app.include_router(recommendations.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        if db.query(Product).count() == 0:
            from app.seed import run as run_seed
            print("[startup] Base vacía, ejecutando seed inicial (rules + cooccurrence; "
                  "LLM solo si GEMINI_API_KEY está configurada)...")
            run_seed()
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}
