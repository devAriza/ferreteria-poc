import { useEffect, useMemo, useState } from "react";
import { api, ApiError, type Product, type Recommendation, type PurchaseResponse } from "../lib/api";
import { useStoreContext } from "../lib/StoreContext";
import { ProductTicket } from "../components/ProductTicket";
import { ReasonBadge } from "../components/Badges";

interface CartLine {
  product: Product;
  cantidad: number;
}

export function PurchasePage() {
  const { selectedStore } = useStoreContext();

  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [cart, setCart] = useState<CartLine[]>([]);
  const [lastAdded, setLastAdded] = useState<Product | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [receipt, setReceipt] = useState<PurchaseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.products.list().then(setProducts);
  }, []);

  useEffect(() => {
    if (!lastAdded || !selectedStore) {
      setRecommendations([]);
      return;
    }
    setLoadingRecs(true);
    api.recommendations
      .get(lastAdded.product_id, selectedStore.tienda_id, 5)
      .then(setRecommendations)
      .catch(() => setRecommendations([]))
      .finally(() => setLoadingRecs(false));
  }, [lastAdded, selectedStore]);

  const filtered = useMemo(() => {
    if (!search.trim()) return products.slice(0, 12);
    const q = search.toLowerCase();
    return products
      .filter(
        (p) =>
          p.nombre.toLowerCase().includes(q) ||
          p.categoria.toLowerCase().includes(q) ||
          p.product_id.toLowerCase().includes(q)
      )
      .slice(0, 12);
  }, [products, search]);

  function addToCart(product: Product) {
    setError(null);
    setCart((prev) => {
      const existing = prev.find((l) => l.product.product_id === product.product_id);
      if (existing) {
        if (existing.cantidad >= product.stock_disponible) return prev;
        return prev.map((l) =>
          l.product.product_id === product.product_id ? { ...l, cantidad: l.cantidad + 1 } : l
        );
      }
      return [...prev, { product, cantidad: 1 }];
    });
    setLastAdded(product);
  }

  function updateQty(productId: string, delta: number) {
    setCart((prev) =>
      prev
        .map((l) =>
          l.product.product_id === productId
            ? { ...l, cantidad: Math.max(0, Math.min(l.cantidad + delta, l.product.stock_disponible)) }
            : l
        )
        .filter((l) => l.cantidad > 0)
    );
  }

  function removeLine(productId: string) {
    setCart((prev) => prev.filter((l) => l.product.product_id !== productId));
  }

  const total = cart.reduce((sum, l) => sum + l.product.precio * l.cantidad, 0);

  async function confirmPurchase() {
    if (!selectedStore || cart.length === 0) return;
    setConfirming(true);
    setError(null);
    try {
      const result = await api.purchases.create({
        tienda_id: selectedStore.tienda_id,
        items: cart.map((l) => ({ product_id: l.product.product_id, cantidad: l.cantidad })),
      });
      setReceipt(result);
      setCart([]);
      setLastAdded(null);
      setRecommendations([]);
      const fresh = await api.products.list();
      setProducts(fresh);
    } catch (e) {
      if (e instanceof ApiError) setError(e.message);
      else setError("Ocurrió un error inesperado al procesar la compra.");
    } finally {
      setConfirming(false);
    }
  }

  if (!selectedStore) {
    return <div className="text-[var(--color-steel)]">Cargando tienda…</div>;
  }

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-xl font-semibold">Venta en {selectedStore.nombre}</h1>
        <p className="eyebrow mt-0.5">
          inventario compartido entre 5 sucursales · clima {selectedStore.clima}
        </p>
      </div>

      {receipt && (
        <div className="mb-5 shelf-ticket rounded-sm p-4 border-l-4 border-l-[var(--color-ok)]">
          <div className="flex items-center justify-between">
            <div className="font-semibold text-[var(--color-ok)]">
              Venta confirmada · ticket {receipt.ticket_id}
            </div>
            <button
              onClick={() => setReceipt(null)}
              className="text-xs text-[var(--color-steel)] hover:text-[var(--color-ink)]"
            >
              cerrar ✕
            </button>
          </div>
          <ul className="mt-2 text-sm font-mono text-[var(--color-ink-soft)]">
            {receipt.items.map((it) => (
              <li key={it.product_id}>
                {it.cantidad}× {it.product_id} — ${it.precio_unitario.toFixed(2)} c/u · quedan{" "}
                {it.stock_restante} en inventario
              </li>
            ))}
          </ul>
          <div className="mt-1 font-mono font-semibold">Total: ${receipt.total.toFixed(2)}</div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Catálogo / búsqueda */}
        <div className="lg:col-span-2">
          <input
            type="text"
            placeholder="Buscar producto por nombre, SKU o categoría…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white border border-[var(--color-steel-line)] rounded-sm px-3 py-2 text-sm
                       focus:outline-none focus:border-[var(--color-safety)] mb-4"
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
            {filtered.map((p) => (
              <ProductTicket key={p.product_id} product={p} onAdd={() => addToCart(p)} compact />
            ))}
            {filtered.length === 0 && (
              <div className="col-span-full text-sm text-[var(--color-steel)] py-8 text-center">
                Sin resultados para "{search}"
              </div>
            )}
          </div>

          {/* Recomendaciones del último producto agregado */}
          {lastAdded && (
            <div className="mt-6">
              <h2 className="text-sm font-semibold mb-1">
                Quien lleva <span className="text-[var(--color-safety)]">{lastAdded.nombre}</span> también necesita…
              </h2>
              <p className="eyebrow mb-3">
                sugerido para {selectedStore.nombre} · solo productos con existencia
              </p>
              {loadingRecs && <div className="text-sm text-[var(--color-steel)]">Calculando…</div>}
              {!loadingRecs && recommendations.length === 0 && (
                <div className="text-sm text-[var(--color-steel)]">
                  Sin sugerencias con existencia disponible para este producto todavía.
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                {recommendations.map((rec) => (
                  <ProductTicket
                    key={rec.product.product_id}
                    product={rec.product}
                    onAdd={() => addToCart(rec.product)}
                    compact
                    footer={
                      <div className="px-3 pb-2.5 flex flex-wrap gap-1">
                        {rec.reasons.map((r, i) => (
                          <ReasonBadge key={i} reason={r} />
                        ))}
                      </div>
                    }
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Carrito */}
        <div>
          <div className="shelf-ticket rounded-sm sticky top-24">
            <div className="px-4 pt-4 pb-2 flex items-center justify-between">
              <span className="font-semibold text-sm">Ticket de venta</span>
              <span className="eyebrow">{cart.length} producto(s)</span>
            </div>
            <div className="shelf-ticket-perf mx-4" />
            <div className="px-4 py-3 max-h-96 overflow-y-auto">
              {cart.length === 0 && (
                <div className="text-sm text-[var(--color-steel)] py-6 text-center">
                  Agrega productos del catálogo
                </div>
              )}
              {cart.map((line) => (
                <div key={line.product.product_id} className="flex items-center justify-between py-2 border-b border-[var(--color-steel-line)] last:border-0">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium truncate">{line.product.nombre}</div>
                    <div className="font-mono text-xs text-[var(--color-steel)]">
                      ${line.product.precio.toFixed(2)} × {line.cantidad}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 ml-2">
                    <button
                      onClick={() => updateQty(line.product.product_id, -1)}
                      className="w-6 h-6 flex items-center justify-center border border-[var(--color-steel-line)] rounded-sm hover:border-[var(--color-safety)] text-sm"
                    >
                      −
                    </button>
                    <span className="font-mono text-sm w-4 text-center">{line.cantidad}</span>
                    <button
                      onClick={() => updateQty(line.product.product_id, 1)}
                      disabled={line.cantidad >= line.product.stock_disponible}
                      className="w-6 h-6 flex items-center justify-center border border-[var(--color-steel-line)] rounded-sm hover:border-[var(--color-safety)] text-sm disabled:opacity-30"
                    >
                      +
                    </button>
                    <button
                      onClick={() => removeLine(line.product.product_id)}
                      className="ml-1 text-[var(--color-danger)] text-xs hover:underline"
                    >
                      quitar
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="shelf-ticket-perf mx-4" />
            <div className="px-4 py-3">
              <div className="flex items-center justify-between font-mono font-semibold mb-3">
                <span>Total</span>
                <span>${total.toFixed(2)}</span>
              </div>
              {error && (
                <div className="text-xs bg-[var(--color-danger-dim)] text-[var(--color-danger)] rounded-sm px-2 py-1.5 mb-2">
                  {error}
                </div>
              )}
              <button
                onClick={confirmPurchase}
                disabled={cart.length === 0 || confirming}
                className="w-full bg-[var(--color-ink)] text-white font-medium py-2.5 rounded-sm
                           hover:bg-[var(--color-safety)] transition-colors
                           disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {confirming ? "Procesando…" : "Confirmar venta"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
