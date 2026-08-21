# Ferretería POC — Inventario compartido + Recomendaciones

Prueba técnica — Desarrollador Senior Fullstack, Área de Innovación.

Sistema de inventario multi-tienda (bolsa compartida entre Cancún, Chihuahua,
CDMX, Monterrey y Mérida) con un motor de recomendación híbrido que sugiere
qué más llevar dado un producto y una tienda.

---

## Cómo levantarlo

### Backend

```bash
cd backend
python -m venv venv
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Al arrancar por primera vez, si la base está vacía, `main.py` corre el seed
automáticamente: carga `data/products.csv`, `data/stores.csv`,
`data/sales.csv`, y genera las relaciones de `rules` + `cooccurrence` (y
`llm` si `GEMINI_API_KEY` está configurada). Documentación interactiva en
`http://localhost:8000/docs`.

Para forzar un re-seed manual:

```bash
python -m app.seed              # incluye LLM si hay API key
python -m app.seed --no-llm     # se salta el enriquecimiento por LLM
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env             # VITE_API_URL=http://localhost:8000
npm run dev                      # http://localhost:3000
```

### Variables de entorno

**`backend/.env`** (ver `backend/.env.example` para el archivo completo):

| Variable                                                           | Default                     | Descripción                                                                                                     |
| ------------------------------------------------------------------ | --------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`                                                     | `sqlite:///./ferreteria.db` | Conexión SQLAlchemy                                                                                             |
| `DATA_DIR`                                                         | `../data`                   | Carpeta con los CSV fuente                                                                                      |
| `GEMINI_API_KEY`                                                   | _(vacío)_                   | Habilita el motor de relaciones por LLM. Sin ella, el sistema sigue funcionando 100% con reglas + co-ocurrencia |
| `GEMINI_MODEL`                                                     | `gemini-2.0-flash`          | Modelo de Gemini a usar                                                                                         |
| `FRONTEND_ORIGIN`                                                  | `http://localhost:3000`     | CORS                                                                                                            |
| `WEIGHT_LLM_RULES` / `WEIGHT_COOCCURRENCE` / `WEIGHT_MANUAL_BOOST` | `0.45` / `0.40` / `0.15`    | Pesos del score combinado                                                                                       |
| `CLIMATE_BOOST_FACTOR` / `CLIMATE_PENALTY_FACTOR`                  | `1.3` / `0.6`               | Ajuste por clima de tienda                                                                                      |

**`frontend/.env`**: solo `VITE_API_URL`.

### Probar el motor de LLM (Gemini) con tu propia key

1. Consigue una API key gratis en https://aistudio.google.com/apikey
2. Ponla en `backend/.env` como `GEMINI_API_KEY=...`
3. Corre `python -m app.seed` (o borra `ferreteria.db` y reinicia el server)
4. Revisa `/admin/relations?source=llm` para ver lo que Gemini infirió, con
   su explicación en español.

Si la key falta o la llamada falla por categoría, el seed lo reporta en
consola y sigue con las demás fuentes — no tumba el sistema (ver
`enrich_catalog_by_category` en `llm_client.py`).

---

## El problema y cómo lo traduje en solución

El cliente pidió "subir las ventas con un sistema de recomendaciones". El
brief mismo da la pista más importante: _"lo que sirve tierra adentro no
siempre sirve frente al mar, y esas relaciones no siempre están en los datos
de venta."_ Eso descarta, a propósito, la solución obvia de un solo motor de
co-ocurrencia (market basket clásico) como respuesta completa: un motor así
solo puede aprender relaciones que **ya ocurrieron** en las ventas, y el
cliente está diciendo explícitamente que las relaciones que más importan
(compatibilidad de material, contexto climático) casi no están ahí.

| Señal                                       | Qué captura                                                                                                                              | Qué NO puede capturar                                                             |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **Reglas de atributos** (`rules_engine.py`) | Compatibilidad funcional por material/categoría/uso, sin depender de ventas                                                              | Semántica fina (es keyword-matching, no entiende lenguaje)                        |
| **LLM** (`llm_client.py`, Gemini)           | Lo mismo que reglas pero con comprensión real del lenguaje — "esto necesita aquello para instalarse" aunque no compartan ninguna palabra | Nada que las reglas no tengan, pero con mejor recall (ver validación abajo)       |
| **Co-ocurrencia** (`cooccurrence.py`)       | Patrones reales de compra, incluyendo hábitos que ningún experto anticiparía                                                             | Productos nuevos o combos raros en venta, aunque sean funcionalmente obligatorios |

Encima de las tres, un **ajuste por clima de tienda** (costero vs interior)
prioriza variantes resistentes a corrosión en sucursales costeras — la señal
que el brief dice que no está en los datos de venta, así que no podía
salir de ahí; sale de una regla explícita sobre el atributo `material`.

Todo esto se combina en `recommendation_engine.py` con pesos configurables
(`WEIGHT_*` en `.env`), y **cada relación queda guardada con su fuente y su
explicación** en la tabla `product_relations` — el negocio la ve y la ajusta
desde `/admin` en el frontend (aceptar, rechazar, o crear una a mano).

## Estructura del repo

```
data/                       CSVs generados (products, stores, sales) + script que los generó
backend/
  app/
    main.py                 entrypoint FastAPI
    config.py                todas las env vars centralizadas
    models.py / schemas.py   SQLAlchemy / Pydantic
    seed.py                  carga CSV -> DB + genera relaciones iniciales
    routers/                 products, stores, sales (compras), recommendations, admin
    services/
      inventory_service.py   descuento atomico, no-sobreventa
      rules_engine.py        motor de reglas por atributos
      cooccurrence.py        market-basket / lift sobre ventas
      llm_client.py          conector Gemini
      recommendation_engine.py  combina las 3 señales + clima
  scripts/
    evaluate_recommendations.py   leave-one-out sobre sales.csv
    evaluate_curated_combos.py    validación contra set de referencia curado
frontend/
  src/
    lib/api.ts               cliente API tipado
    lib/StoreContext.tsx     tienda seleccionada (persistente)
    components/              Layout, StoreSelector, ProductTicket, Badges
    pages/
      PurchasePage.tsx        flujo de compra + recomendaciones en vivo
      CatalogPage.tsx          CRUD de productos
      AdminRelationsPage.tsx   auditoría/ajuste de relaciones
```
