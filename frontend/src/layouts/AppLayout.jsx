import { matchPath, NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import Icon from "../components/Icon";
import "./AppLayout.css";

const navigation = [
  { label: "Products", title: "Product Management", path: "/products", icon: "products" },
  { label: "Inventory", path: "/inventory", icon: "inventory" },
  { label: "Suppliers", path: "/suppliers", icon: "suppliers" },
  { label: "Transactions", path: "/transactions", icon: "transactions" },
  { label: "Reports", path: "/reports", icon: "reports", adminOnly: true },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();

  const currentPage = navigation.find(({ path }) =>
    matchPath(path, pathname)
  );

  const visibleNavigation = navigation.filter(
    ({ adminOnly }) => !adminOnly || user?.role === "admin"
  );

  const username = user?.username;
  const initial = username?.slice(0, 1).toUpperCase();

  return (
    <div className="app-shell">
      <a className="ui-button skip-link" href="#workspace-content">
        Skip to content
      </a>

      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <Icon name="bolt" />
          </span>

          <div className="brand-text">
            <span className="brand-name">ElectroStock</span>
            <span className="brand-caption">Inventory management</span>
          </div>
        </div>

        <nav className="workspace-nav" aria-label="Workspace">
          <p className="nav-heading" aria-hidden="true">
            Workspace
          </p>

          <ul className="navigation">
            {visibleNavigation.map(({ icon, label, path }) => (
              <li key={path}>
                <NavLink className="nav-link" to={path}>
                  <Icon name={icon} />
                  <span>{label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" aria-hidden="true" />
          Inventory workspace
        </div>
      </aside>

      <div className="main-panel">
        <header className="topbar">
          <div className="breadcrumb">
            <span className="breadcrumb-parent">Workspace</span>
            <Icon name="chevron" />
            <span className="breadcrumb-current" aria-current="page">
              {currentPage?.title ?? currentPage?.label ?? "Workspace"}
            </span>
          </div>

          <div className="topbar-account">
            {username && (
              <div className="topbar-identity">
                <span className="account-avatar" aria-hidden="true">
                  {initial}
                </span>
                <span className="topbar-username" title={username}>
                  {username}
                </span>
              </div>
            )}

            {user?.role && (
              <span className="topbar-role">{user.role}</span>
            )}

            <button
              className="ui-button ui-button--secondary logout-button"
              type="button"
              onClick={logout}
            >
              <Icon name="logout" />
              Log out
            </button>
          </div>
        </header>

        <main
          className="page-content"
          id="workspace-content"
          tabIndex={-1}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}