import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import AppLayout from "./layouts/AppLayout";
import ProductsPage from "./pages/products/ProductsPage";
import InventoryPage from "./pages/inventory/InventoryPage";
import ReportsPage from "./pages/reports/ReportsPage";
import LoginPage from "./pages/auth/LoginPage";

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
  const { user } = useAuth();
  const location = useLocation();

  function requireRole(element, role) {
    if (!user) {
      return (
        <Navigate
          to="/login"
          replace
          state={{ from: location.pathname }}
        />
      );
    }
    if (role && user.role !== role) {
      return <Navigate to="/products" replace />;
    }
    return element;
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/products" replace />} />

        <Route path="products" element={requireRole(<ProductsPage />)} />
        <Route path="inventory" element={requireRole(<InventoryPage />)} />
        <Route
          path="reports"
          element={requireRole(<ReportsPage />, "admin")}
        />

        <Route
          path="suppliers"
          element={requireRole(<PlaceholderPage title="Suppliers" />)}
        />
        <Route
          path="transactions"
          element={requireRole(<PlaceholderPage title="Transactions" />)}
        />

        <Route path="*" element={<Navigate to="/products" replace />} />
      </Route>
    </Routes>
  );
}
