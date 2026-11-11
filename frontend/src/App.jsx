import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import AppLayout from "./layouts/AppLayout";
import LoginPage from "./pages/auth/LoginPage";
import ProductsPage from "./pages/products/ProductsPage";
import InventoryPage from "./pages/inventory/InventoryPage";
import ReportsPage from "./pages/reports/ReportsPage";

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
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/products" replace />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route
          path="reports"
          element={
            <ProtectedRoute role="admin">
              <ReportsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="suppliers"
          element={<PlaceholderPage title="Suppliers" />}
        />
        <Route
          path="transactions"
          element={<PlaceholderPage title="Transactions" />}
        />
        <Route path="*" element={<Navigate to="/products" replace />} />
      </Route>
    </Routes>
  );
}
