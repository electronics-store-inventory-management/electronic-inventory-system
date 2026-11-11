
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import "./AppLayout.css";

const navigation = [
  { label: "Products", path: "/products" },
  { label: "Inventory", path: "/inventory" },
  { label: "Suppliers", path: "/suppliers" },
  { label: "Transactions", path: "/transactions" },
  { label: "Reports", path: "/reports", adminOnly: true },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const visibleNavigation = navigation.filter(
    (item) => !item.adminOnly || user?.role === "admin",
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">E</div>
          <div>
            <h1>ElectroStock</h1>
            <p>Inventory management</p>
          </div>
        </div>

        <p className="nav-heading">WORKSPACE</p>

        <nav className="navigation">
          {visibleNavigation.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `nav-link${isActive ? " active" : ""}`
              }
            >
              {item.label}
              {item.path === "/products" && (
                <span className="nav-indicator">●</span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          Inventory workspace
        </div>
      </aside>

      <div className="main-panel">
        <header className="topbar">
          <div>
            <span className="breadcrumb">Workspace</span>
            <span className="breadcrumb-separator"> / </span>
            <span className="breadcrumb-current">Product Management</span>
          </div>
          <div className="topbar-account">
            <span className="topbar-username">{user?.username}</span>
            <span className="topbar-role">{user?.role}</span>
            <button
              className="logout-button"
              type="button"
              onClick={logout}
            >
              Sign out
            </button>
          </div>
        </header>

        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
