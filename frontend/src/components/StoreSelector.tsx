import { useStoreContext } from "../lib/StoreContext";

const CLIMA_LABEL: Record<string, string> = {
  costero: "Costero",
  interior: "Interior",
};

export function StoreSelector() {
  const { stores, selectedStore, setSelectedStoreId, loading } = useStoreContext();

  if (loading) {
    return <div className="eyebrow">Cargando tiendas…</div>;
  }

  return (
    <div className="flex items-center gap-2">
      <span className="eyebrow hidden sm:inline">Tienda</span>
      <div className="relative">
        <select
          value={selectedStore?.tienda_id ?? ""}
          onChange={(e) => setSelectedStoreId(e.target.value)}
          className="appearance-none bg-[var(--color-ink)] text-white font-mono text-sm font-medium
                     pl-3 pr-8 py-2 rounded-sm border border-[var(--color-ink)]
                     hover:border-[var(--color-safety)] transition-colors cursor-pointer"
        >
          {stores.map((s) => (
            <option key={s.tienda_id} value={s.tienda_id}>
              {s.nombre} · {CLIMA_LABEL[s.clima]}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-white/60">
          ▾
        </span>
      </div>
    </div>
  );
}
