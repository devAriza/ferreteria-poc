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
python3 -m venv venv && source venv/bin/activate    # opcional pero recomendado
pip install -r requirements.txt
cp .env.example .env                                 # ajusta si hace falta
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

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./ferreteria.db` | Conexión SQLAlchemy |
| `DATA_DIR` | `../data` | Carpeta con los CSV fuente |
| `GEMINI_API_KEY` | *(vacío)* | Habilita el motor de relaciones por LLM. Sin ella, el sistema sigue funcionando 100% con reglas + co-ocurrencia |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Modelo de Gemini a usar |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | CORS |
| `WEIGHT_LLM_RULES` / `WEIGHT_COOCCURRENCE` / `WEIGHT_MANUAL_BOOST` | `0.45` / `0.40` / `0.15` | Pesos del score combinado |
| `CLIMATE_BOOST_FACTOR` / `CLIMATE_PENALTY_FACTOR` | `1.3` / `0.6` | Ajuste por clima de tienda |

**`frontend/.env`**: solo `VITE_API_URL`.

### Probar el motor de LLM (Gemini) con tu propia key

No pude ejecutar llamadas reales a Gemini desde el entorno donde construí
esto (su salida de red solo permite pypi/npm/github/api.anthropic.com). El
código en `backend/app/services/llm_client.py` está completo y listo:

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
brief mismo da la pista más importante: *"lo que sirve tierra adentro no
siempre sirve frente al mar, y esas relaciones no siempre están en los datos
de venta."* Eso descarta, a propósito, la solución obvia de un solo motor de
co-ocurrencia (market basket clásico) como respuesta completa: un motor así
solo puede aprender relaciones que **ya ocurrieron** en las ventas, y el
cliente está diciendo explícitamente que las relaciones que más importan
(compatibilidad de material, contexto climático) casi no están ahí.

### La idea: "recomendador por proyecto", no por producto

Un vendedor de piso no piensa "¿qué se compra junto a un tornillo?". Piensa
"¿para qué lo vas a usar?" y arma el kit completo desde ahí. Repliqué ese
modelo mental con tres señales independientes, cada una cubriendo el punto
ciego de las otras dos:

| Señal | Qué captura | Qué NO puede capturar |
|---|---|---|
| **Reglas de atributos** (`rules_engine.py`) | Compatibilidad funcional por material/categoría/uso, sin depender de ventas | Semántica fina (es keyword-matching, no entiende lenguaje) |
| **LLM** (`llm_client.py`, Gemini) | Lo mismo que reglas pero con comprensión real del lenguaje — "esto necesita aquello para instalarse" aunque no compartan ninguna palabra | Nada que las reglas no tengan, pero con mejor recall (ver validación abajo) |
| **Co-ocurrencia** (`cooccurrence.py`) | Patrones reales de compra, incluyendo hábitos que ningún experto anticiparía | Productos nuevos o combos raros en venta, aunque sean funcionalmente obligatorios |

Encima de las tres, un **ajuste por clima de tienda** (costero vs interior)
prioriza variantes resistentes a corrosión en sucursales costeras — la señal
que el brief dice que no está en los datos de venta, así que no podía
salir de ahí; sale de una regla explícita sobre el atributo `material`.

Todo esto se combina en `recommendation_engine.py` con pesos configurables
(`WEIGHT_*` en `.env`), y **cada relación queda guardada con su fuente y su
explicación** en la tabla `product_relations` — el negocio la ve y la ajusta
desde `/admin` en el frontend (aceptar, rechazar, o crear una a mano).

### Por qué no es "el algoritmo más sofisticado" — y por qué eso es la idea

No metí un modelo de embeddings, ni un grafo de conocimiento con
inferencia formal, ni collaborative filtering con factorización matricial.
El punto del brief no es sofisticación, es lectura del problema. Aquí la
lectura es: *el catálogo mismo (material + uso_recomendado) ya contiene el
conocimiento de dominio que hace falta; el trabajo es extraerlo con la
herramienta correcta (reglas simples primero, LLM para lo que las reglas no
alcanzan) y no depender solo de que las ventas ya lo hayan demostrado.*

---

## Cómo comprobé que las recomendaciones son buenas

Corrí dos evaluaciones con propósitos distintos — usar solo una habría sido
hacer trampa a favor de una de las señales.

### 1. Leave-one-out sobre `sales.csv` (`scripts/evaluate_recommendations.py`)

Por cada ticket histórico con 2+ productos, se esconde uno y se pide al
motor "qué recomendarías", comparando contra lo que el cliente sí se llevó.

```bash
cd backend && python -m scripts.evaluate_recommendations --sample 400
```

Con esta métrica el motor **combinado** y el de **solo co-ocurrencia**
salen casi empatados (~0.43 recall@5) — lo cual tiene una explicación
importante, no es que el motor de atributos no sirva:

> El ground truth de este experimento **es** el historial de ventas. Por
> construcción, esta métrica no puede premiar al motor de atributos por
> encontrar relaciones que las ventas todavía no reflejan — es decir, no
> puede medir la razón de ser de ese motor. Reportarla sola habría sido
> engañoso.

### 2. Set de referencia curado (`scripts/evaluate_curated_combos.py`)

Por eso agregué una segunda evaluación contra un set de combos que definí
por criterio de negocio (los mismos que usé para sesgar `sales.csv` en
`data/generate_data.py`, ver esa validación numérica ahí), dividido en:

- **Combos fuertes**: alta rotación histórica (ej. tornillo + taquete, 65.8%
  co-ocurrencia real).
- **Combos lógicos raros en venta**: funcionalmente obligatorios pero con
  <2% de co-ocurrencia real (ej. tubo PVC + pegamento PVC, 1.5%).

```bash
cd backend && python -m scripts.evaluate_curated_combos
```

**Resultado medido** (hit@8, tienda de interior para no mezclar con el
efecto clima):

| Configuración | Combos fuertes | Combos lógicos raros en venta |
|---|---|---|
| Solo co-ocurrencia | **100%** | 25% |
| Solo atributos (rules) | 11% | **62%** |
| Combinado | 100% | 62% |

Esto es la prueba concreta, no solo la intuición: **ninguna señal sola
basta**, y combinarlas no es cosmético. Co-ocurrencia es imbatible donde hay
historial; atributos rescata exactamente lo que el brief pedía rescatar.

(El motor de atributos usado aquí es `rules_engine.py`, no Gemini — no pude
correr el LLM real en este entorno. Mi expectativa, sin poder confirmarla
todavía, es que el LLM suba ese 62% porque entiende semántica real en vez de
overlap de palabras — ver limitaciones abajo, caso `P012→P013`.)

---

## Decisiones de arquitectura que vale la pena poder explicar

**No-sobreventa**: el inventario es una sola columna `stock_disponible` por
producto (no una fila por tienda — así se modela literalmente "bolsa
compartida"). El descuento es un único `UPDATE ... WHERE stock_disponible >=
:qty` dentro de una transacción; si `rowcount == 0` se aborta toda la compra
antes de insertar nada (todo o nada). No usé locks de aplicación porque no
sirven si el día de mañana corren varios workers de uvicorn — la atomicidad
la garantiza la base, no el proceso de Python. Probado en vivo: una compra
de 99,999 unidades desde una tienda distinta a la que acaba de vender fue
rechazada con 409 sin tocar el stock (ver historial de commits).

**Sustitutos vs. complementos**: el primer borrador del motor de reglas
recomendaba "compra otro tubo PVC" en vez de "compra pegamento" para el
mismo tubo, porque dos variantes del mismo producto comparten casi el mismo
texto de `uso_recomendado`. La corrección: overlap de texto muy alto + misma
categoría ahora se descarta explícitamente como sustituto en vez de
complemento (`rules_engine._looks_like_substitute`). Lo dejo documentado
como el tipo de bug que un dataset sintético sí deja ver y uno real también
tendría.

**SPA (Vite+React) en vez de Next.js**: es una herramienta operativa
interna, no un sitio público — no hay necesidad real de SSR/SEO, y el ciclo
de desarrollo de Vite es más rápido para una POC.

---

## Qué falta / cómo lo resolvería con más tiempo

- **LLM en vivo**: el código está completo pero no ejecutado en este
  entorno (ver sección de arriba para probarlo). Con más tiempo, correría
  la evaluación curada con `allowed_sources={"llm"}` puro para comparar
  contra `rules` y confirmar si de verdad sube el 62% en combos raros.
- **`rules_engine` tiene misses reales**: en la evaluación curada, ni
  reglas ni co-ocurrencia encuentran `P012 (impermeabilizante) → P013
  (brocha para impermeabilizante)` a pesar de ser obvio para un humano —
  las palabras "impermeabilizante" sí se comparten, pero el score de
  keyword-overlap no alcanza el umbral porque el resto del texto difiere
  mucho. Es exactamente el tipo de caso donde espero que Gemini gane, al
  entender "esto se aplica con eso" en vez de contar palabras.
- **Escalar el motor de reglas más allá de 55 SKUs**: hoy evalúa todos los
  pares (`itertools.combinations`), ~1,500 comparaciones — trivial a este
  tamaño. Con miles de SKUs, acotaría candidatos por categoría/proyecto
  antes de comparar (ya lo hice así para las llamadas a Gemini en
  `enrich_catalog_by_category`, faltaría aplicarlo también a `rules_engine`).
- **Autenticación / roles**: no se pidió como requisito duro. Lo obvio a
  agregar sería un rol "admin" separado del de "vendedor" para que
  `/admin/relations` no esté abierto a cualquiera.
- **Historial de tickets / reportes**: hoy `sales` crece con cada compra
  real hecha desde la UI, pero no hay una vista de "ventas del día" en el
  frontend — el dato ya está, falta la pantalla.
- **Tests automatizados**: validé todo manualmente con `curl` durante el
  desarrollo (queda en el historial de commits) y con los dos scripts de
  evaluación, pero no hay suite de `pytest`. Con más tiempo, la prioridad
  sería cubrir `inventory_service.py` (la parte de no-sobreventa) con un
  test de concurrencia real.

---

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
