const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface Store {
  tienda_id: string;
  nombre: string;
  clima: "costero" | "interior";
}

export interface Product {
  product_id: string;
  nombre: string;
  categoria: string;
  material: string;
  uso_recomendado: string;
  precio: number;
  unidad: string;
  stock_disponible: number;
}

export interface RecommendationReason {
  source: "llm" | "rules" | "cooccurrence" | "manual" | "clima";
  score: number;
  explanation: string;
}

export interface Recommendation {
  product: Product;
  combined_score: number;
  reasons: RecommendationReason[];
}

export interface PurchaseItemResult {
  product_id: string;
  cantidad: number;
  precio_unitario: number;
  stock_restante: number;
}

export interface PurchaseResponse {
  ticket_id: string;
  tienda_id: string;
  fecha: string;
  items: PurchaseItemResult[];
  total: number;
}

export interface ProductRelation {
  id: number;
  product_a: string;
  product_b: string;
  source: "llm" | "rules" | "cooccurrence" | "manual";
  score: number;
  explanation: string;
  status: "active" | "rejected";
  created_at: string;
  updated_at: string;
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  stores: {
    list: () => request<Store[]>("/stores"),
  },
  products: {
    list: (params?: { categoria?: string; q?: string }) => {
      const qs = new URLSearchParams();
      if (params?.categoria) qs.set("categoria", params.categoria);
      if (params?.q) qs.set("q", params.q);
      const suffix = qs.toString() ? `?${qs}` : "";
      return request<Product[]>(`/products${suffix}`);
    },
    get: (id: string) => request<Product>(`/products/${id}`),
    create: (payload: Product) =>
      request<Product>("/products", { method: "POST", body: JSON.stringify(payload) }),
    update: (id: string, payload: Partial<Product>) =>
      request<Product>(`/products/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
    remove: (id: string) => request<void>(`/products/${id}`, { method: "DELETE" }),
  },
  purchases: {
    create: (payload: { tienda_id: string; items: { product_id: string; cantidad: number }[] }) =>
      request<PurchaseResponse>("/purchases", { method: "POST", body: JSON.stringify(payload) }),
  },
  recommendations: {
    get: (product_id: string, tienda_id: string, top_k = 5) =>
      request<Recommendation[]>(
        `/recommendations?product_id=${product_id}&tienda_id=${tienda_id}&top_k=${top_k}`
      ),
  },
  admin: {
    listRelations: (params?: { product_id?: string; source?: string; status?: string }) => {
      const qs = new URLSearchParams();
      if (params?.product_id) qs.set("product_id", params.product_id);
      if (params?.source) qs.set("source", params.source);
      if (params?.status) qs.set("status", params.status);
      const suffix = qs.toString() ? `?${qs}` : "";
      return request<ProductRelation[]>(`/admin/relations${suffix}`);
    },
    createRelation: (payload: { product_a: string; product_b: string; score: number; explanation: string }) =>
      request<ProductRelation>("/admin/relations", { method: "POST", body: JSON.stringify(payload) }),
    updateRelationStatus: (id: number, status: "active" | "rejected") =>
      request<ProductRelation>(`/admin/relations/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    deleteRelation: (id: number) => request<void>(`/admin/relations/${id}`, { method: "DELETE" }),
  },
};

export { ApiError };
