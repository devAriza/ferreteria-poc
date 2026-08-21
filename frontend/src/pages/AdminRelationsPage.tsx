import { useEffect, useState } from "react";
import { api, ApiError, type Product, type ProductRelation } from "../lib/api";

const SOURCE_META: Record<string, { label: string; className: string }> = {
  llm: { label: "IA · Gemini", className: "bg-[var(--color-navy)] text-white" },
  rules: { label: "Regla de atributos", className: "bg-[var(--color-steel-line)] text-[var(--color-ink)]" },
  cooccurrence: { label: "Historial de venta", className: "bg-[var(--color-ok-dim)] text-[var(--color-ok)]" },
  manual: { label: "Manual", className: "bg-[var(--color-safety-dim)] text-[var(--color-safety)]" },
};

export function AdminRelationsPage() {
  const [relations, setRelations] = useState<ProductRelation[]>([]);
  const [products, setProducts] = useState<Record<string, Product>>({});
  const [sourceFilter, setSourceFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("active");
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualForm, setManualForm] = useState({ product_a: "", product_b: "", score: 0.8, explanation: "" });
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api.admin
      .listRelations({
        source: sourceFilter || undefined,
        status: statusFilter || undefined,
      })
      .then(setRelations);
  }

  useEffect(refresh, [sourceFilter, statusFilter]);

  useEffect(() => {
    api.products.list().then((list) => {
      const map: Record<string, Product> = {};
      list.forEach((p) => (map[p.product_id] = p));
      setProducts(map);
    });
  }, []);

  async function setStatus(id: number, status: "active" | "rejected") {
    await api.admin.updateRelationStatus(id, status);
    refresh();
  }

  async function createManual() {
    setError(null);
    try {
      await api.admin.createRelation(manualForm);
      setShowManualForm(false);
      setManualForm({ product_a: "", product_b: "", score: 0.8, explanation: "" });
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al crear la relación");
    }
  }

  function name(id: string) {
    return products[id]?.nombre ?? id;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-xl font-semibold">Relaciones del motor de recomendación</h1>
        <button
          onClick={() => setShowManualForm((v) => !v)}
          className="bg-[var(--color-safety)] text-white text-sm font-medium px-4 py-2 rounded-sm hover:bg-[var(--color-ink)] transition-colors"
        >
          + Relación manual
        </button>
      </div>
      <p className="eyebrow mb-4">
        de dónde sale cada sugerencia y con qué peso · acepta, rechaza o fuerza relaciones
      </p>

      {showManualForm && (
        <div className="shelf-ticket rounded-sm p-4 mb-4">
          <div className="font-semibold text-sm mb-3">Nueva relación manual</div>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <label className="block">
              <span className="eyebrow block mb-1">Producto A (SKU)</span>
              <input
                className="input"
                value={manualForm.product_a}
                onChange={(e) => setManualForm({ ...manualForm, product_a: e.target.value })}
                placeholder="P001"
              />
            </label>
            <label className="block">
              <span className="eyebrow block mb-1">Producto B (SKU)</span>
              <input
                className="input"
                value={manualForm.product_b}
                onChange={(e) => setManualForm({ ...manualForm, product_b: e.target.value })}
                placeholder="P005"
              />
            </label>
            <label className="block">
              <span className="eyebrow block mb-1">Score (0-1)</span>
              <input
                type="number"
                min={0}
                max={1}
                step={0.05}
                className="input"
                value={manualForm.score}
                onChange={(e) => setManualForm({ ...manualForm, score: parseFloat(e.target.value) })}
              />
            </label>
            <label className="block sm:col-span-1">
              <span className="eyebrow block mb-1">Motivo</span>
              <input
                className="input"
                value={manualForm.explanation}
                onChange={(e) => setManualForm({ ...manualForm, explanation: e.target.value })}
                placeholder="Combo que arma el vendedor en piso"
              />
            </label>
          </div>
          {error && (
            <div className="text-xs bg-[var(--color-danger-dim)] text-[var(--color-danger)] rounded-sm px-2 py-1.5 mt-3">
              {error}
            </div>
          )}
          <button
            onClick={createManual}
            className="mt-3 bg-[var(--color-ink)] text-white text-sm font-medium px-4 py-2 rounded-sm hover:bg-[var(--color-safety)] transition-colors"
          >
            Crear relación
          </button>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="input w-auto bg-white"
        >
          <option value="">Todas las fuentes</option>
          <option value="llm">IA · Gemini</option>
          <option value="rules">Regla de atributos</option>
          <option value="cooccurrence">Historial de venta</option>
          <option value="manual">Manual</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="input w-auto bg-white"
        >
          <option value="active">Activas</option>
          <option value="rejected">Rechazadas</option>
          <option value="">Todas</option>
        </select>
      </div>

      <div className="shelf-ticket rounded-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[var(--color-paper-dim)] text-left">
              <th className="px-3 py-2 eyebrow">Producto A</th>
              <th className="px-3 py-2 eyebrow">Producto B</th>
              <th className="px-3 py-2 eyebrow">Fuente</th>
              <th className="px-3 py-2 eyebrow">Score</th>
              <th className="px-3 py-2 eyebrow">Explicación</th>
              <th className="px-3 py-2 eyebrow"></th>
            </tr>
          </thead>
          <tbody>
            {relations.map((r) => {
              const meta = SOURCE_META[r.source] ?? { label: r.source, className: "bg-gray-200" };
              return (
                <tr key={r.id} className="border-t border-[var(--color-steel-line)] align-top">
                  <td className="px-3 py-2">
                    <div className="font-medium">{name(r.product_a)}</div>
                    <div className="font-mono text-xs text-[var(--color-steel)]">{r.product_a}</div>
                  </td>
                  <td className="px-3 py-2">
                    <div className="font-medium">{name(r.product_b)}</div>
                    <div className="font-mono text-xs text-[var(--color-steel)]">{r.product_b}</div>
                  </td>
                  <td className="px-3 py-2">
                    <span className={`text-[0.65rem] font-mono font-medium uppercase px-1.5 py-0.5 rounded-sm ${meta.className}`}>
                      {meta.label}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono">{r.score.toFixed(2)}</td>
                  <td className="px-3 py-2 text-xs text-[var(--color-ink-soft)] max-w-xs">{r.explanation}</td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    {r.status === "active" ? (
                      <button
                        onClick={() => setStatus(r.id, "rejected")}
                        className="text-xs text-[var(--color-danger)] hover:underline"
                      >
                        rechazar
                      </button>
                    ) : (
                      <button
                        onClick={() => setStatus(r.id, "active")}
                        className="text-xs text-[var(--color-ok)] hover:underline"
                      >
                        reactivar
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
            {relations.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-[var(--color-steel)]">
                  Sin relaciones para este filtro
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <style>{`
        .input {
          background: white;
          border: 1px solid var(--color-steel-line);
          border-radius: 2px;
          padding: 0.5rem 0.65rem;
          font-size: 0.875rem;
        }
        .input:focus { outline: none; border-color: var(--color-safety); }
      `}</style>
    </div>
  );
}
