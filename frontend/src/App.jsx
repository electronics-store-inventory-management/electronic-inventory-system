
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import ProductsPage from "./pages/products/ProductsPage";

function PlaceholderPage({ title }) {
  return (
    <section>
      <p className="eyebrow">WORKSPACE</p>
      <h1>{title}</h1>
      <p className="page-description">
        This module will be added by its assigned contributor.
      </p>
    </section>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/products" replace />} />
        <Route path="products" element={<ProductsPage />} />
        <Route
          path="inventory"
          element={<PlaceholderPage title="Inventory" />}
        />
        <Route
          path="suppliers"
          element={<PlaceholderPage title="Suppliers" />}
        />
        <Route
          path="transactions"
          element={<PlaceholderPage title="Transactions" />}
        />
        <Route
          path="reports"
          element={<PlaceholderPage title="Reports" />}
        />
        <Route path="*" element={<Navigate to="/products" replace />} />
      </Route>
    </Routes>
  );
}
