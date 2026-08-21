import { useEffect, useState } from "react";
import { api, ApiError, type Product } from "../lib/api";
import { StockBadge } from "../components/Badges";

const EMPTY_FORM: Product = {
  product_id: "",
  nombre: "",
  categoria: "",
  material: "",
  uso_recomendado: "",
  precio: 0,
  unidad: "pieza",
  stock_disponible: 0,
};

export function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Product | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<Product>(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api.products.list().then(setProducts);
  }

  useEffect(refresh, []);

  const filtered = products.filter((p) => {
    const q = search.toLowerCase();
    return (
      p.nombre.toLowerCase().includes(q) ||
      p.product_id.toLowerCase().includes(q) ||
      p.categoria.toLowerCase().includes(q)
    );
  });

  function startEdit(p: Product) {
    setEditing(p);
    setCreating(false);
    setForm(p);
    setError(null);
  }

  function startCreate() {
    setCreating(true);
    setEditing(null);
    setForm(EMPTY_FORM);
    setError(null);
  }

  function cancelForm() {
    setEditing(null);
    setCreating(false);
    setError(null);
  }

  async function save() {
    setError(null);
    try {
      if (creating) {
        await api.products.create(form);
      } else if (editing) {
        const { product_id, ...rest } = form;
        await api.products.update(editing.product_id, rest);
      }
      cancelForm();
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al guardar el producto");
    }
  }

  async function remove(id: string) {
    if (!confirm(`¿Eliminar el producto ${id}? Esta acción no se puede deshacer.`)) return;
    try {
      await api.products.remove(id);
      refresh();
    } catch (e) {
      alert(e instanceof ApiError ? e.message : "Error al eliminar");
    }
  }

  const formOpen = creating || editing !== null;

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold">Catálogo</h1>
          <p className="eyebrow mt-0.5">{products.length} productos · bolsa de inventario compartida</p>
        </div>
        <button
          onClick={startCreate}
          className="bg-[var(--color-safety)] text-white text-sm font-medium px-4 py-2 rounded-sm hover:bg-[var(--color-ink)] transition-colors"
        >
          + Nuevo producto
        </button>
      </div>

      {formOpen && (
        <div className="shelf-ticket rounded-sm p-4 mb-5">
          <div className="font-semibold text-sm mb-3">
            {creating ? "Nuevo producto" : `Editando ${editing?.product_id}`}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {creating && (
              <Field label="SKU (product_id)">
                <input
                  className="input"
                  value={form.product_id}
                  onChange={(e) => setForm({ ...form, product_id: e.target.value })}
                  placeholder="P999"
                />
              </Field>
            )}
            <Field label="Nombre">
              <input
                className="input"
                value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value })}
              />
            </Field>
            <Field label="Categoría">
              <input
                className="input"
                value={form.categoria}
                onChange={(e) => setForm({ ...form, categoria: e.target.value })}
              />
            </Field>
            <Field label="Material">
              <input
                className="input"
                value={form.material}
                onChange={(e) => setForm({ ...form, material: e.target.value })}
              />
            </Field>
            <Field label="Unidad">
              <input
                className="input"
                value={form.unidad}
                onChange={(e) => setForm({ ...form, unidad: e.target.value })}
              />
            </Field>
            <Field label="Precio">
              <input
                type="number"
                step="0.01"
                className="input"
                value={form.precio}
                onChange={(e) => setForm({ ...form, precio: parseFloat(e.target.value) || 0 })}
              />
            </Field>
            <Field label="Stock disponible">
              <input
                type="number"
                className="input"
                value={form.stock_disponible}
                onChange={(e) => setForm({ ...form, stock_disponible: parseInt(e.target.value) || 0 })}
              />
            </Field>
            <Field label="Uso recomendado" full>
              <textarea
                className="input"
                rows={2}
                value={form.uso_recomendado}
                onChange={(e) => setForm({ ...form, uso_recomendado: e.target.value })}
              />
            </Field>
          </div>
          {error && (
            <div className="text-xs bg-[var(--color-danger-dim)] text-[var(--color-danger)] rounded-sm px-2 py-1.5 mt-3">
              {error}
            </div>
          )}
          <div className="flex gap-2 mt-3">
            <button
              onClick={save}
              className="bg-[var(--color-ink)] text-white text-sm font-medium px-4 py-2 rounded-sm hover:bg-[var(--color-safety)] transition-colors"
            >
              Guardar
            </button>
            <button
              onClick={cancelForm}
              className="text-sm text-[var(--color-steel)] px-4 py-2 hover:text-[var(--color-ink)]"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      <input
        type="text"
        placeholder="Buscar por nombre, SKU o categoría…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full bg-white border border-[var(--color-steel-line)] rounded-sm px-3 py-2 text-sm focus:outline-none focus:border-[var(--color-safety)] mb-4"
      />

      <div className="shelf-ticket rounded-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[var(--color-paper-dim)] text-left">
              <th className="px-3 py-2 font-mono text-xs eyebrow">SKU</th>
              <th className="px-3 py-2 eyebrow">Nombre</th>
              <th className="px-3 py-2 eyebrow">Categoría</th>
              <th className="px-3 py-2 eyebrow">Precio</th>
              <th className="px-3 py-2 eyebrow">Stock</th>
              <th className="px-3 py-2 eyebrow"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr key={p.product_id} className="border-t border-[var(--color-steel-line)] hover:bg-[var(--color-paper-dim)]/50">
                <td className="px-3 py-2 font-mono text-xs">{p.product_id}</td>
                <td className="px-3 py-2 font-medium">{p.nombre}</td>
                <td className="px-3 py-2 text-[var(--color-steel)]">{p.categoria}</td>
                <td className="px-3 py-2 font-mono">${p.precio.toFixed(2)}</td>
                <td className="px-3 py-2">
                  <StockBadge stock={p.stock_disponible} />
                </td>
                <td className="px-3 py-2 text-right whitespace-nowrap">
                  <button onClick={() => startEdit(p)} className="text-xs text-[var(--color-navy)] hover:underline mr-3">
                    editar
                  </button>
                  <button onClick={() => remove(p.product_id)} className="text-xs text-[var(--color-danger)] hover:underline">
                    eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <style>{`
        .input {
          width: 100%;
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

function Field({ label, children, full }: { label: string; children: React.ReactNode; full?: boolean }) {
  return (
    <label className={`block ${full ? "sm:col-span-2" : ""}`}>
      <span className="eyebrow block mb-1">{label}</span>
      {children}
    </label>
  );
}
