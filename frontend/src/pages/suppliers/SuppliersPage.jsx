import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../../auth/useAuth";
import Icon from "../../components/Icon";
import { supplierService } from "../../services/supplierService";
import {
  Alert,
  PageHeading,
  WorkspaceCard,
  WorkspaceState,
  WorkspaceStats,
  WorkspaceTable,
} from "../shared/WorkspaceTools";
import "./SuppliersPage.css";

const EMPTY_SUPPLIER = { name: "", email: "", phone: "", address: "" };

function validateSupplier(supplier) {
  const errors = {};
  const name = supplier.name.trim();
  const email = supplier.email.trim();
  const phone = supplier.phone.trim();
  const address = supplier.address.trim();
  if (!name) errors.name = "Enter a supplier name.";
  else if (name.length > 100) errors.name = "Use 100 characters or fewer.";
  if (email && (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email) || email.length > 254)) {
    errors.email = "Enter a valid email address (254 characters or fewer).";
  }
  const containsControlCharacter = (value) =>
    Array.from(value).some((character) => character.codePointAt(0) < 32);
  if (phone && (phone.length > 50 || containsControlCharacter(phone))) {
    errors.phone = "Use up to 50 characters without control characters.";
  }
  if (address && (address.length > 200 || containsControlCharacter(address))) {
    errors.address = "Use up to 200 characters without control characters.";
  }
  return errors;
}

function SupplierForm({ mode, supplier, onClose, onSaved }) {
  const [values, setValues] = useState(supplier ?? EMPTY_SUPPLIER);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [saving, setSaving] = useState(false);
  const modalRef = useRef(null);
  const nameRef = useRef(null);

  useEffect(() => {
    nameRef.current?.focus();
    function onKeyDown(event) {
      if (event.key === "Escape" && !saving) onClose();
      if (event.key !== "Tab") return;
      const controls = modalRef.current?.querySelectorAll('button:not([disabled]), input:not([disabled])');
      if (!controls?.length) return;
      if (event.shiftKey && document.activeElement === controls[0]) {
        event.preventDefault();
        controls[controls.length - 1].focus();
      } else if (!event.shiftKey && document.activeElement === controls[controls.length - 1]) {
        event.preventDefault();
        controls[0].focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, saving]);

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = validateSupplier(values);
    setErrors(nextErrors);
    setSubmitError("");
    if (Object.keys(nextErrors).length) return;
    setSaving(true);
    const payload = {
      name: values.name.trim(),
      email: values.email.trim() || (mode === "create" ? null : undefined),
      phone: values.phone.trim() || (mode === "create" ? null : undefined),
      address: values.address.trim() || (mode === "create" ? null : undefined),
    };
    try {
      if (mode === "edit") await supplierService.update(supplier.id, payload);
      else await supplierService.create(payload);
      await onSaved(mode === "edit" ? "Supplier updated successfully." : "Supplier added successfully.");
    } catch (error) {
      setSubmitError(error.message || `Unable to ${mode === "edit" ? "update" : "add"} supplier.`);
    } finally {
      setSaving(false);
    }
  }

  function updateField(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  const fields = [
    { key: "name", label: "Supplier name", required: true, maxLength: 100, type: "text" },
    { key: "email", label: "Email address", maxLength: 254, type: "email" },
    { key: "phone", label: "Phone number", maxLength: 50, type: "tel" },
    { key: "address", label: "Address", maxLength: 200, type: "text" },
  ];

  return (
    <div className="ui-dialog-backdrop" onMouseDown={(event) => event.target === event.currentTarget && !saving && onClose()}>
      <section ref={modalRef} className="ui-dialog supplier-dialog" role="dialog" aria-modal="true" aria-labelledby="supplier-form-title">
        <header className="supplier-dialog-head">
          <span className="workspace-icon ui-tone-info"><Icon name="suppliers" /></span>
          <div>
            <h2 id="supplier-form-title">{mode === "edit" ? "Edit supplier" : "Add supplier"}</h2>
          <p>Keep supplier contact information up to date.</p>
          </div>
          <button className="ui-button ui-button--secondary ui-button--icon" type="button" aria-label="Close form" onClick={onClose} disabled={saving}><Icon name="close" /></button>
        </header>
        <form className="supplier-form" onSubmit={handleSubmit} noValidate>
          {submitError && <Alert>{submitError}</Alert>}
          {fields.map(({ key, label, required, maxLength, type }, index) => (
            <label className="supplier-form-field" htmlFor={`supplier-${key}`} key={key}>
              <span>{label}{required && <> <span aria-hidden="true">*</span></>}</span>
              <input
                ref={index === 0 ? nameRef : undefined}
                className="ui-field"
                id={`supplier-${key}`}
                name={key}
                type={type}
                value={values[key] ?? ""}
                required={required}
                maxLength={maxLength}
                aria-invalid={Boolean(errors[key])}
                aria-describedby={errors[key] ? `supplier-${key}-error` : undefined}
                onChange={(event) => updateField(key, event.target.value)}
              />
              {errors[key] && <small id={`supplier-${key}-error`}>{errors[key]}</small>}
            </label>
          ))}
          <footer className="product-form-actions">
            <button className="ui-button ui-button--secondary" type="button" onClick={onClose} disabled={saving}>Cancel</button>
            <button className="ui-button" type="submit" disabled={saving}>{saving ? "Saving…" : mode === "edit" ? "Save changes" : "Add supplier"}</button>
          </footer>
        </form>
      </section>
    </div>
  );
}

export default function SuppliersPage() {
  const { user } = useAuth();
  const canManage = user?.role === "admin";
  const [suppliers, setSuppliers] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formMode, setFormMode] = useState("");
  const [editingSupplier, setEditingSupplier] = useState(null);
  const [success, setSuccess] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const addRef = useRef(null);
  const editRef = useRef(null);

  const loadSuppliers = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    else setRefreshing(true);
    setError("");
    try {
      const result = await supplierService.list();
      setSuppliers(result);
      return true;
    } catch (err) {
      setError(err.message || "Unable to load suppliers.");
      return false;
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    supplierService.list().then((result) => {
      if (cancelled) return;
      setSuppliers(result);
    }).catch((err) => {
      if (!cancelled) setError(err.message || "Unable to load suppliers.");
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  const filteredSuppliers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    if (!query) return suppliers;
    return suppliers.filter((supplier) =>
      [supplier.name, supplier.email, supplier.phone, supplier.address, String(supplier.id)]
        .some((value) => value?.toLocaleLowerCase().includes(query)),
    );
  }, [search, suppliers]);

  async function handleSaved(message) {
    setFormMode("");
    setEditingSupplier(null);
    setSuccess(message);
    const refreshed = await loadSuppliers();
    if (!refreshed) setSuccess(`${message} The list could not refresh; use Refresh to try again.`);
    requestAnimationFrame(() => (editingSupplier ? editRef.current : addRef.current)?.focus());
  }

  function closeForm() {
    setFormMode("");
    setEditingSupplier(null);
    requestAnimationFrame(() => (editingSupplier ? editRef.current : addRef.current)?.focus());
  }

  function openEdit(supplier, trigger) {
    editRef.current = trigger;
    setEditingSupplier({ ...supplier });
    setFormMode("edit");
    setSuccess("");
  }

  return (
    <div className="workspace-page suppliers-page">
      <PageHeading
        title="Suppliers"
        description="Manage supplier contacts and keep your product supply network organized."
        action={canManage ? <button ref={addRef} className="ui-button" type="button" onClick={() => { setSuccess(""); setFormMode("create"); }}><Icon name="add" /> Add supplier</button> : null}
      />

      <Alert success>{success}</Alert>

      <WorkspaceStats label="Supplier summary" loading={loading} error={error} metrics={[
        { title: "Total suppliers", value: suppliers.length, icon: "suppliers", tone: "info" },
      ]} />

      <WorkspaceCard id="supplier-directory-title" title="Supplier directory" detail={<span className="workspace-card-value"><span>Matching suppliers</span><strong>{loading ? "—" : filteredSuppliers.length}</strong></span>}>
        <div className="supplier-filters">
          <label className="catalogue-field" htmlFor="supplier-search">Search suppliers
            <span className="catalogue-field-control"><Icon name="search" /><input id="supplier-search" className="ui-field" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, email, phone or address" /></span>
          </label>
          <button className="ui-button ui-button--secondary" type="button" onClick={() => loadSuppliers()} disabled={loading || refreshing}><Icon name="refresh" />{refreshing ? "Refreshing…" : "Refresh"}</button>
        </div>
        {loading ? <WorkspaceState title="Loading suppliers" /> : error ? <WorkspaceState title="Could not load suppliers" description={error} icon="warning" tone="error" action={<button className="ui-button ui-button--secondary" type="button" onClick={() => loadSuppliers(true)}>Try again</button>} /> : filteredSuppliers.length === 0 ? (
          <WorkspaceState title={suppliers.length ? "No matching suppliers" : "No suppliers yet"} description={suppliers.length ? "Try a different search term." : canManage ? "Add your first supplier to build your directory." : "Suppliers will appear here when they are added."} icon="suppliers" action={canManage && !suppliers.length ? <button className="ui-button" type="button" onClick={() => setFormMode("create")}><Icon name="add" /> Add supplier</button> : null} />
        ) : (
          <WorkspaceTable label="Supplier directory" wide>
            <thead><tr><th scope="col">Supplier</th><th scope="col">Email</th><th scope="col">Phone</th><th scope="col">Address</th>{canManage && <th scope="col">Actions</th>}</tr></thead>
            <tbody>{filteredSuppliers.map((supplier) => <tr key={supplier.id}>
              <th scope="row"><div className="supplier-identity"><span className="supplier-avatar" aria-hidden="true">{supplier.name.charAt(0).toUpperCase()}</span><span><strong>{supplier.name}</strong><span className="workspace-product-id">SUP-{String(supplier.id).padStart(4, "0")}</span></span></div></th>
              <td>{supplier.email || "—"}</td><td>{supplier.phone || "—"}</td><td className="supplier-address">{supplier.address || "—"}</td>
              {canManage && <td><div className="supplier-row-actions"><button className="ui-button ui-button--secondary ui-button--icon" type="button" aria-label={`Edit ${supplier.name}`} title="Edit supplier" onClick={(event) => openEdit(supplier, event.currentTarget)}><Icon name="edit" /></button></div></td>}
            </tr>)}</tbody>
          </WorkspaceTable>
        )}
      </WorkspaceCard>

      {formMode && <SupplierForm key={`${formMode}-${editingSupplier?.id ?? "new"}`} mode={formMode} supplier={editingSupplier} onClose={closeForm} onSaved={handleSaved} />}
    </div>
  );
}
