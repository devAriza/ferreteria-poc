import { BrowserRouter, Routes, Route } from "react-router-dom";
import { StoreProvider } from "./lib/StoreContext";
import { Layout } from "./components/Layout";
import { PurchasePage } from "./pages/PurchasePage";
import { CatalogPage } from "./pages/CatalogPage";
import { AdminRelationsPage } from "./pages/AdminRelationsPage";

export default function App() {
  return (
    <StoreProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<PurchasePage />} />
            <Route path="/catalogo" element={<CatalogPage />} />
            <Route path="/admin" element={<AdminRelationsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </StoreProvider>
  );
}
