import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type Store } from "./api";

interface StoreContextValue {
  stores: Store[];
  selectedStore: Store | null;
  setSelectedStoreId: (id: string) => void;
  loading: boolean;
}

const StoreContext = createContext<StoreContextValue | undefined>(undefined);

const STORAGE_KEY = "ferreteria.tienda_id";

export function StoreProvider({ children }: { children: ReactNode }) {
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(
    () => localStorage.getItem(STORAGE_KEY)
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.stores
      .list()
      .then((data) => {
        setStores(data);
        setSelectedId((current) => {
          if (current && data.some((s) => s.tienda_id === current)) return current;
          return data[0]?.tienda_id ?? null;
        });
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedId) localStorage.setItem(STORAGE_KEY, selectedId);
  }, [selectedId]);

  const selectedStore = stores.find((s) => s.tienda_id === selectedId) ?? null;

  return (
    <StoreContext.Provider
      value={{ stores, selectedStore, setSelectedStoreId: setSelectedId, loading }}
    >
      {children}
    </StoreContext.Provider>
  );
}

export function useStoreContext() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStoreContext debe usarse dentro de <StoreProvider>");
  return ctx;
}
