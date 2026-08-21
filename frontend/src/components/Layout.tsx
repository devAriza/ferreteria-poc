import { NavLink, Outlet } from "react-router-dom";
import { StoreSelector } from "./StoreSelector";

const NAV_ITEMS = [
  { to: "/", label: "Comprar", end: true },
  { to: "/catalogo", label: "Catálogo" },
  { to: "/admin", label: "Relaciones (admin)" },
];

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-[var(--color-ink)] text-white sticky top-0 z-20 border-b-4 border-[var(--color-safety)]">
        <div className="max-w-6xl mx-auto px-5 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[var(--color-safety)] flex items-center justify-center font-mono font-bold text-sm">
              FR
            </div>
            <div>
              <div className="font-semibold leading-tight">Ferretería · Inventario</div>
              <div className="eyebrow text-white/50 leading-tight">bolsa compartida · 5 sucursales</div>
            </div>
          </div>
          <StoreSelector />
        </div>
        <nav className="max-w-6xl mx-auto px-5 flex gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
                  isActive
                    ? "border-[var(--color-safety)] text-white"
                    : "border-transparent text-white/60 hover:text-white"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="flex-1 paper-texture">
        <div className="max-w-6xl mx-auto px-5 py-6">
          <Outlet />
        </div>
      </main>
      <footer className="text-center py-4 eyebrow">
        Prueba técnica · Sistema de recomendación de ferretería · POC
      </footer>
    </div>
  );
}
