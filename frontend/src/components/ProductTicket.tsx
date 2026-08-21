import type { Product } from "../lib/api";
import { StockBadge } from "./Badges";

interface ProductTicketProps {
  product: Product;
  onAdd?: () => void;
  disabled?: boolean;
  compact?: boolean;
  footer?: React.ReactNode;
}

export function ProductTicket({ product, onAdd, disabled, compact, footer }: ProductTicketProps) {
  return (
    <div className="shelf-ticket rounded-sm shadow-sm hover:shadow-md transition-shadow flex flex-col">
      <div className="px-3 pt-3 pb-2">
        <div className="flex items-start justify-between gap-2">
          <span className="eyebrow">{product.product_id}</span>
          <StockBadge stock={product.stock_disponible} />
        </div>
        <div className={`font-semibold leading-snug mt-1 ${compact ? "text-sm" : "text-base"}`}>
          {product.nombre}
        </div>
        <div className="text-xs text-[var(--color-steel)] mt-1">
          {product.categoria} · {product.material}
        </div>
        {!compact && (
          <div className="text-xs text-[var(--color-ink-soft)] mt-1.5 leading-snug">
            {product.uso_recomendado}
          </div>
        )}
      </div>
      <div className="shelf-ticket-perf mx-3" />
      <div className="px-3 py-2.5 flex items-center justify-between">
        <div className="font-mono font-semibold">
          ${product.precio.toLocaleString("es-MX", { minimumFractionDigits: 2 })}
          <span className="text-[var(--color-steel)] font-normal text-xs"> / {product.unidad}</span>
        </div>
        {onAdd && (
          <button
            onClick={onAdd}
            disabled={disabled || product.stock_disponible === 0}
            className="bg-[var(--color-safety)] text-white text-sm font-medium px-3 py-1.5 rounded-sm
                       hover:bg-[var(--color-ink)] transition-colors
                       disabled:bg-[var(--color-steel-line)] disabled:text-[var(--color-steel)] disabled:cursor-not-allowed"
          >
            Agregar
          </button>
        )}
      </div>
      {footer}
    </div>
  );
}
