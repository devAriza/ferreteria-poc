"""
Generador de datos sintéticos para la POC de la ferretería.

No se proporcionaron products.csv / sales.csv, así que este script los construye
a propósito con tres características que sostienen la propuesta de solución:

1. Catálogo con `material` y `uso_recomendado` ricos en texto libre, para que un
   motor basado en LLM/reglas pueda inferir compatibilidad funcional real
   (ej. "tubo PVC 1/2" + "pegamento PVC" + "cinta teflón").

2. Variantes de material por resistencia ambiental (acero estándar vs
   galvanizado vs inoxidable) para simular el caso "tierra adentro vs costa"
   que el cliente menciona explícitamente.

3. Ventas con sesgo intencional:
   - Fuerte co-ocurrencia real en combos "de caja" (tornillo+taquete, cable+contacto)
     -> esto SÍ lo captura un motor de market-basket clásico.
   - Combos lógicamente obvios pero de bajo volumen histórico (tubo+pegamento+teflón,
     impermeabilizante+brocha) -> el motor de co-ocurrencia los subestima porque hay
     pocas transacciones, aunque funcionalmente siempre van juntos. Este hueco es lo
     que el motor de reglas/LLM debe rescatar.
   - Sesgo climático: tiendas costeras (Cancún, Mérida) compran desproporcionadamente
     más variantes galvanizadas/inoxidables; tiendas de interior compran más la
     variante estándar (más barata).

Reproducible: mismo seed -> mismos CSVs.
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

# ---------------------------------------------------------------------------
# Tiendas (se guarda aparte porque el inventario es una sola bolsa compartida;
# las tiendas solo aportan contexto de venta y clima)
# ---------------------------------------------------------------------------
STORES = [
    {"tienda_id": "CUN", "nombre": "Cancún",     "clima": "costero"},
    {"tienda_id": "MID", "nombre": "Mérida",     "clima": "costero"},
    {"tienda_id": "CHI", "nombre": "Chihuahua",  "clima": "interior"},
    {"tienda_id": "CDMX","nombre": "CDMX",       "clima": "interior"},
    {"tienda_id": "MTY", "nombre": "Monterrey",  "clima": "interior"},
]

# ---------------------------------------------------------------------------
# Catálogo de productos
# categoria / material / uso_recomendado son las señales semánticas clave
# ---------------------------------------------------------------------------
PRODUCTS = [
    # --- Plomería / PVC ---
    ("P001","Tubo PVC hidráulico 1/2\" x 6m","Plomería","PVC","Conducción de agua fría, instalaciones domésticas",145.00,"pieza",40),
    ("P002","Tubo PVC hidráulico 3/4\" x 6m","Plomería","PVC","Conducción de agua fría, instalaciones domésticas",180.00,"pieza",35),
    ("P003","Codo PVC 90° 1/2\"","Plomería","PVC","Cambio de dirección en tubería hidráulica",8.50,"pieza",120),
    ("P004","Coples PVC 1/2\"","Plomería","PVC","Unión de tramos de tubería PVC",6.00,"pieza",150),
    ("P005","Pegamento PVC 118ml","Plomería","Solvente/PVC","Sellado y unión permanente de tubería PVC",65.00,"pieza",60),
    ("P006","Cinta teflón 1/2\" x 10m","Plomería","PTFE","Sellado de roscas en conexiones de agua y gas",12.00,"pieza",200),
    ("P007","Llave de paso PVC 1/2\"","Plomería","PVC/Latón","Corte de flujo de agua en instalación doméstica",95.00,"pieza",45),
    ("P008","Regadera sencilla ABS","Plomería","ABS","Instalación de baño, uso doméstico",180.00,"pieza",25),
    ("P009","Manguera flexible para WC 30cm","Plomería","Acero inoxidable/PVC","Conexión de tinaco o tanque de baño",85.00,"pieza",30),
    ("P010","Flotador para tinaco","Plomería","Plástico ABS","Control de nivel de agua en tinacos",120.00,"pieza",18),
    ("P011","Cemento gris 50kg","Construcción","Cemento Portland","Obra gris, fijación de tubería enterrada, bases",210.00,"saco",50),
    ("P012","Impermeabilizante acrílico 19L","Construcción","Acrílico","Protección de techos y azoteas contra filtraciones",980.00,"cubeta",15),
    ("P013","Brocha para impermeabilizante 4\"","Herramientas","Cerdas sintéticas","Aplicación de impermeabilizante y selladores",45.00,"pieza",40),

    # --- Tornillería: mismo tipo de tornillo en 3 materiales (clave para clima) ---
    ("P020","Tornillo autorroscante 1\" acero estándar (100pz)","Tornillería","Acero al carbón","Fijación general en interiores, no expuesto a intemperie",55.00,"bolsa",70),
    ("P021","Tornillo autorroscante 1\" galvanizado (100pz)","Tornillería","Acero galvanizado","Fijación en exteriores y zonas de humedad moderada",85.00,"bolsa",55),
    ("P022","Tornillo autorroscante 1\" acero inoxidable (100pz)","Tornillería","Acero inoxidable 304","Fijación en exteriores costeros, alta resistencia a corrosión salina",150.00,"bolsa",30),
    ("P023","Taquete de plástico 1/4\" (100pz)","Tornillería","Nylon/PVC","Anclaje de tornillos en concreto y tabique",40.00,"bolsa",90),
    ("P024","Taquete metálico expansión 3/8\"","Tornillería","Acero zincado","Anclaje de cargas pesadas en concreto",6.00,"pieza",100),
    ("P025","Tuerca hexagonal 1/4\" galvanizada (50pz)","Tornillería","Acero galvanizado","Sujeción en estructuras metálicas exteriores",35.00,"bolsa",45),
    ("P026","Clavo para concreto 2\" (1kg)","Tornillería","Acero endurecido","Fijación directa en concreto y block",65.00,"kg",40),
    ("P027","Bisagra de piso acero inoxidable","Herrajes","Acero inoxidable 304","Puertas de vidrio y exteriores costeros",320.00,"pieza",12),
    ("P028","Bisagra de piso acero estándar","Herrajes","Acero al carbón","Puertas interiores, bajo uso",180.00,"pieza",18),
    ("P029","Candado 40mm acero estándar","Seguridad","Acero al carbón","Uso interior, bodegas techadas",95.00,"pieza",25),
    ("P030","Candado 40mm acero inoxidable","Seguridad","Acero inoxidable","Exteriores, alta humedad, zonas costeras",180.00,"pieza",15),

    # --- Eléctrico ---
    ("P040","Cable THW cal.12 (rollo 100m)","Eléctrico","Cobre/PVC","Instalación eléctrica residencial entubada",1450.00,"rollo",12),
    ("P041","Contacto doble polarizado","Eléctrico","Termoplástico/cobre","Instalación de tomacorrientes en interiores",35.00,"pieza",80),
    ("P042","Apagador sencillo","Eléctrico","Termoplástico","Control de encendido de iluminación interior",28.00,"pieza",75),
    ("P043","Cinta aislante 3/4\" x 20m","Eléctrico","PVC","Aislamiento de empalmes eléctricos",18.00,"pieza",100),
    ("P044","Caja octagonal galvanizada","Eléctrico","Acero galvanizado","Alojamiento de conexiones de lámparas y ventiladores",22.00,"pieza",60),
    ("P045","Foco LED 9W luz cálida","Eléctrico","Aluminio/plástico","Iluminación interior residencial",45.00,"pieza",90),
    ("P046","Lámpara exterior LED IP65","Eléctrico","Aluminio/policarbonato","Iluminación exterior resistente a lluvia y humedad",280.00,"pieza",20),
    ("P047","Extensión eléctrica 5m","Eléctrico","Cobre/PVC","Uso doméstico general",95.00,"pieza",35),
    ("P048","Pastilla termomagnética 20A","Eléctrico","Termoplástico/cobre","Protección de circuitos en centro de carga",180.00,"pieza",25),

    # --- Pintura ---
    ("P060","Pintura vinílica blanca 19L","Pintura","Vinil-acrílico","Interiores y exteriores, acabado mate",850.00,"cubeta",20),
    ("P061","Esmalte anticorrosivo 1L","Pintura","Alquidálico","Protección de superficies metálicas contra oxidación, exteriores",165.00,"pieza",30),
    ("P062","Sellador para exteriores 4L","Pintura","Acrílico","Preparación de muros expuestos a humedad antes de pintar",320.00,"cubeta",15),
    ("P063","Rodillo para pintura 9\"","Herramientas","Espuma/felpa","Aplicación de pintura vinílica en muros",45.00,"pieza",50),
    ("P064","Brocha 3\" cerdas sintéticas","Herramientas","Cerdas sintéticas","Pintura de detalle y esmaltes",38.00,"pieza",55),
    ("P065","Lija de agua grano 220 (paquete 5pz)","Pintura","Óxido de aluminio","Preparación de superficie antes de pintar",30.00,"paquete",40),
    ("P066","Thinner estándar 1L","Pintura","Solvente","Dilución de esmaltes y limpieza de brochas",55.00,"pieza",45),

    # --- Jardín / exterior ---
    ("P080","Manguera para jardín 15m","Jardín","PVC reforzado","Riego de jardín y lavado de exteriores",280.00,"pieza",22),
    ("P081","Aspersor giratorio","Jardín","Plástico ABS/latón","Riego automático de áreas verdes",65.00,"pieza",30),
    ("P082","Conector rápido para manguera","Jardín","Latón","Acople rápido de manguera a llave de jardín",25.00,"pieza",50),
    ("P083","Guantes de carnaza","Seguridad","Carnaza/algodón","Protección en trabajos de jardinería y construcción",65.00,"par",60),
    ("P084","Costal de block hueco 15cm","Construcción","Concreto","Construcción de muros y bardas",18.00,"pieza",200),
    ("P085","Malla ciclónica galvanizada 1m x 20m","Construcción","Acero galvanizado","Cercado perimetral, resistente a intemperie",980.00,"rollo",8),
    ("P086","Malla ciclónica acero estándar 1m x 20m","Construcción","Acero al carbón","Cercado perimetral en interiores/patios techados",650.00,"rollo",10),

    # --- Herramientas ---
    ("P100","Taladro percutor 1/2\" 650W","Herramientas","Metal/plástico ABS","Perforación en concreto, madera y metal",1250.00,"pieza",15),
    ("P101","Broca para concreto 1/4\"","Herramientas","Carburo de tungsteno","Perforación en concreto y tabique",35.00,"pieza",70),
    ("P102","Broca para concreto 3/8\"","Herramientas","Carburo de tungsteno","Perforación en concreto y tabique para taquetes de expansión",45.00,"pieza",60),
    ("P103","Martillo de uña 16oz","Herramientas","Acero forjado/madera","Uso general, fijación de clavos",120.00,"pieza",30),
    ("P104","Desarmador plano/cruz set 6pz","Herramientas","Acero cromado","Uso general en instalaciones eléctricas y ensamblado",95.00,"set",40),
    ("P105","Llave inglesa 10\"","Herramientas","Acero al cromo vanadio","Ajuste de tuercas y conexiones de plomería",145.00,"pieza",25),
    ("P106","Cinta métrica 5m","Herramientas","Acero/ABS","Medición general en obra e instalación",55.00,"pieza",45),
    ("P107","Nivel de burbuja 60cm","Herramientas","Aluminio","Verificación de horizontalidad en instalaciones",165.00,"pieza",20),
]

# ---------------------------------------------------------------------------
# Combos "de caja registradora": alta co-ocurrencia real y frecuente.
# Esto es lo que un motor de market-basket clásico va a detectar sin problema.
# ---------------------------------------------------------------------------
STRONG_COMBOS = [
    ("P020", "P023"),  # tornillo estándar + taquete plástico
    ("P021", "P023"),  # tornillo galvanizado + taquete plástico
    ("P022", "P023"),  # tornillo inox + taquete plástico
    ("P041", "P043"),  # contacto + cinta aislante
    ("P042", "P043"),  # apagador + cinta aislante
    ("P063", "P060"),  # rodillo + pintura vinílica
    ("P064", "P061"),  # brocha + esmalte
    ("P100", "P101"),  # taladro + broca 1/4
    ("P100", "P102"),  # taladro + broca 3/8
]

# ---------------------------------------------------------------------------
# Combos "lógicos pero raros en venta": funcionalmente siempre deberían ir
# juntos, pero en el historial aparecen poco (compras separadas, stock previo,
# clientes que ya tenían una de las dos piezas). Este es el hueco que el
# motor de reglas/LLM debe rescatar y que la co-ocurrencia subestima.
# ---------------------------------------------------------------------------
WEAK_BUT_LOGICAL_COMBOS = [
    ("P001", "P005"),  # tubo PVC + pegamento PVC
    ("P001", "P006"),  # tubo PVC + cinta teflón
    ("P002", "P005"),
    ("P007", "P006"),  # llave de paso + teflón
    ("P012", "P013"),  # impermeabilizante + brocha para impermeabilizante
    ("P062", "P060"),  # sellador exteriores + pintura vinílica
    ("P080", "P082"),  # manguera + conector rápido
    ("P085", "P024"),  # malla ciclónica + taquete metálico expansión
]

# Productos con variante climática explícita (para sesgo costero/interior)
COASTAL_PREFERENCE = {"P022", "P030", "P027", "P046", "P085"}     # inox / IP65 / galvanizado exterior
INLAND_PREFERENCE  = {"P020", "P029", "P028", "P086"}             # estándar, más barato

PRODUCT_IDS = [p[0] for p in PRODUCTS]
PRODUCT_BASE_WEIGHT = {p[0]: random.uniform(0.4, 1.0) for p in PRODUCTS}

def choose_products_for_basket(store_clima):
    """Elige productos de una canasta con sesgo climático + combos definidos."""
    basket = []
    r = random.random()
    if r < 0.35:
        pair = random.choice(STRONG_COMBOS)
        basket.extend(pair)
    elif r < 0.42:
        pair = random.choice(WEAK_BUT_LOGICAL_COMBOS)
        # a propósito, casi siempre solo compran UNO de los dos (esa es la fuga)
        basket.append(random.choice(pair))
    else:
        basket.append(random.choice(PRODUCT_IDS))

    # posible segundo item aleatorio ponderado, con sesgo climático
    if random.random() < 0.5:
        pool = PRODUCT_IDS
        weights = []
        for pid in pool:
            w = PRODUCT_BASE_WEIGHT[pid]
            if store_clima == "costero" and pid in COASTAL_PREFERENCE:
                w *= 4
            if store_clima == "costero" and pid in INLAND_PREFERENCE:
                w *= 0.25
            if store_clima == "interior" and pid in INLAND_PREFERENCE:
                w *= 3
            if store_clima == "interior" and pid in COASTAL_PREFERENCE:
                w *= 0.2
            weights.append(w)
        extra = random.choices(pool, weights=weights, k=1)[0]
        if extra not in basket:
            basket.append(extra)
    return basket


def generate_sales(n_days=120, baskets_per_day_range=(8, 22)):
    rows = []
    sale_id = 1
    start = datetime(2025, 3, 1)
    for d in range(n_days):
        date = start + timedelta(days=d)
        for store in STORES:
            n_baskets = random.randint(*baskets_per_day_range)
            for _ in range(n_baskets):
                basket = choose_products_for_basket(store["clima"])
                ticket_id = f"T{sale_id:06d}"
                for pid in basket:
                    price = next(p[5] for p in PRODUCTS if p[0] == pid)
                    qty = random.choice([1, 1, 1, 2, 2, 3])
                    rows.append({
                        "venta_id": f"V{sale_id:06d}",
                        "ticket_id": ticket_id,
                        "fecha": date.strftime("%Y-%m-%d"),
                        "tienda_id": store["tienda_id"],
                        "product_id": pid,
                        "cantidad": qty,
                        "precio_unitario": price,
                    })
                    sale_id += 1
    return rows


def write_products_csv(path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_id","nombre","categoria","material","uso_recomendado","precio","unidad","stock_disponible"])
        for pid, nombre, cat, mat, uso, precio, unidad, stock in PRODUCTS:
            w.writerow([pid, nombre, cat, mat, uso, precio, unidad, stock])


def write_stores_csv(path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tienda_id","nombre","clima"])
        for s in STORES:
            w.writerow([s["tienda_id"], s["nombre"], s["clima"]])


def write_sales_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["venta_id","ticket_id","fecha","tienda_id","product_id","cantidad","precio_unitario"])
        for r in rows:
            w.writerow([r["venta_id"], r["ticket_id"], r["fecha"], r["tienda_id"], r["product_id"], r["cantidad"], r["precio_unitario"]])


if __name__ == "__main__":
    import os
    out_dir = os.path.dirname(os.path.abspath(__file__))
    write_products_csv(os.path.join(out_dir, "products.csv"))
    write_stores_csv(os.path.join(out_dir, "stores.csv"))
    sales_rows = generate_sales()
    write_sales_csv(os.path.join(out_dir, "sales.csv"), sales_rows)
    print(f"Productos: {len(PRODUCTS)}")
    print(f"Tiendas: {len(STORES)}")
    print(f"Filas de venta: {len(sales_rows)}")
