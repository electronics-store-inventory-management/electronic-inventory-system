import { useEffect, useState } from "react";
import Icon from "../../components/Icon";
import "./Workspace.css";

export function useLoad(loader, deps = []) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      setData(await loader());
    } catch (error) {
      setError(error.message || "Could not load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, deps);

  return { data, loading, error, refresh };
}

export function Alert({ children, success = false }) {
  return children ? (
    <div className={`ui-feedback ${success ? "ui-tone-success" : "ui-tone-error"}`} role="status">
      {children}
    </div>
  ) : null;
}

export function Modal({ title, onClose, children }) {
  return (
    <div className="ui-dialog-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="ui-dialog" role="dialog" aria-modal="true" aria-label={title}>
        <div className="workspace-card-head">
          <h2>{title}</h2>
          <button className="ui-button ui-button--secondary" type="button" onClick={onClose}>Close</button>
        </div>
        {children}
      </section>
    </div>
  );
}

export function PageHeading({ title, description, action }) {
  return (
    <header className="workspace-heading">
      <div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action}
    </header>
  );
}

export function RefreshButton({ children, onClick }) {
  return (
    <button className="ui-button ui-button--secondary" type="button" onClick={onClick}>
      <Icon name="refresh" />
      {children}
    </button>
  );
}

export function WorkspaceStats({ label, metrics, loading, error }) {
  return (
    <dl className="workspace-stats" aria-label={label} aria-busy={loading}>
      {metrics.map(({ title, value, icon, tone }) => (
        <div className="ui-card workspace-stat" key={title}>
          <dt>
            <span className={`workspace-icon ui-tone-${tone}`}><Icon name={icon} /></span>
            {title}
          </dt>
          <dd>{loading || error ? "—" : value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function WorkspaceCard({ id, title, detail, children }) {
  return (
    <section className="ui-card workspace-card" aria-labelledby={id}>
      <header className="workspace-card-head">
        <h2 id={id}>{title}</h2>
        {detail}
      </header>
      {children}
    </section>
  );
}

export function WorkspaceTable({ label, wide = false, children }) {
  return (
    <div className={`workspace-table-frame${wide ? " workspace-table-frame--wide" : ""}`}>
      <p className="workspace-table-hint">Scroll to see all columns.</p>
      <div className="ui-table-scroll workspace-table-scroll" tabIndex={0} role="region" aria-label={label}>
        <table className="ui-table workspace-table">{children}</table>
      </div>
    </div>
  );
}

export function WorkspaceState({ title, description, icon, tone = "info", action }) {
  return (
    <div className="workspace-state">
      <span className={`workspace-icon ui-tone-${tone}`}>
        {icon ? <Icon name={icon} /> : <span className="ui-spinner" aria-hidden="true" />}
      </span>
      <div role={tone === "error" ? "alert" : "status"}>
        <strong>{title}</strong>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function LoadingOrError({ loading, error, loadingTitle, errorTitle, onRetry }) {
  if (loading) return <WorkspaceState title={loadingTitle} />;
  if (error) {
    return (
      <WorkspaceState
        title={errorTitle}
        description={error}
        icon="warning"
        tone="error"
        action={<button className="ui-button ui-button--secondary" type="button" onClick={onRetry}>Try again</button>}
      />
    );
  }
  return null;
}
