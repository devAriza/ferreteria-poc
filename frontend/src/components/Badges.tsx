import type { RecommendationReason } from "../lib/api";

const SOURCE_LABEL: Record<string, { label: string; className: string }> = {
  llm: { label: "IA · Gemini", className: "bg-[var(--color-navy)] text-white" },
  rules: { label: "Regla de atributos", className: "bg-[var(--color-steel-line)] text-[var(--color-ink)]" },
  cooccurrence: { label: "Historial de venta", className: "bg-[var(--color-ok-dim)] text-[var(--color-ok)]" },
  manual: { label: "Ajuste del negocio", className: "bg-[var(--color-safety-dim)] text-[var(--color-safety)]" },
  clima: { label: "Clima de tienda", className: "bg-[var(--color-danger-dim)] text-[var(--color-danger)]" },
};

export function ReasonBadge({ reason }: { reason: RecommendationReason }) {
  const meta = SOURCE_LABEL[reason.source] ?? {
    label: reason.source,
    className: "bg-gray-200 text-gray-700",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm text-[0.65rem] font-mono font-medium uppercase tracking-wide ${meta.className}`}
      title={reason.explanation}
    >
      {meta.label}
    </span>
  );
}

export function StockBadge({ stock }: { stock: number }) {
  let className = "bg-[var(--color-ok-dim)] text-[var(--color-ok)]";
  let label = `${stock} disp.`;
  if (stock === 0) {
    className = "bg-[var(--color-danger-dim)] text-[var(--color-danger)]";
    label = "agotado";
  } else if (stock <= 10) {
    className = "bg-[var(--color-safety-dim)] text-[var(--color-safety)]";
  }
  return (
    <span className={`font-mono text-xs px-1.5 py-0.5 rounded-sm font-medium ${className}`}>
      {label}
    </span>
  );
}
