import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import AuthSessionStatus from "../pages/auth/AuthSessionStatus";
import { PageHeading, WorkspaceState } from "../pages/shared/WorkspaceTools";

export default function ProtectedRoute({
  children,
  role,
  adminOnly = false,
}) {
  const { isAuthenticated, session, user } = useAuth();
  const location = useLocation();

  if (session && !isAuthenticated) {
    return <AuthSessionStatus />;
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: `${location.pathname}${location.search}${location.hash}`,
        }}
      />
    );
  }

  if ((adminOnly || role === "admin") && user?.role !== "admin") {
    return (
      <div className="workspace-page">
        <PageHeading title="Reports" />
        <WorkspaceState
          title="Reports require administrator access"
          icon="lock"
          tone="error"
        />
      </div>
    );
  }

  if (role && user?.role !== role) {
    return <Navigate to="/products" replace />;
  }

  return children;
}
