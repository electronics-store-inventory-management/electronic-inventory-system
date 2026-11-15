
import { useCallback, useEffect, useRef, useState } from "react";
import { supplierService } from "../../services/supplierService";
import "./SuppliersPage.css";

const EMPTY_SUPPLIER = { name: "", email: "", phone: "", address: "" };

function validateSupplier(supplier) {
  const errors = {};

  const name = supplier.name.trim();
  if (!name) errors.name = "Enter a supplier name.";
  else if (name.length > 100) errors.name = "Use 100 characters or fewer.";

  const email = supplier.email.trim();
  if (email) {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = "Enter a valid email address.";
    } else if (email.length > 254) {
      errors.email = "Use 254 characters or fewer.";
    }
  }

  const phone = supplier.phone.trim();
  if (phone && phone.length > 50) {
    errors.phone = "Use 50 characters or fewer.";
  }

  const address = supplier.address.trim();
  if (address && address.length > 200) {
    errors.address = "Use 200 characters or fewer.";
  }

  return errors;
}

async function fetchSuppliers() {
  try {
    return { suppliers: await supplierService.list(), error: "" };
  } catch (err) {
    return { suppliers: [], error: err.message || "Unable to load suppliers." };
  }
}

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [newSupplier, setNewSupplier] = useState(EMPTY_SUPPLIER);
  const [formErrors, setFormErrors] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  const addButtonRef = useRef(null);

  const loadSuppliers = useCallback(async () => {
    setLoading(true);
    setError("");
    const result = await fetchSuppliers();
    if (result.error) setError(result.error);
    else setSuppliers(result.suppliers);
    setLoading(false);
    return !result.error;
  }, []);

  const closeAddForm = useCallback(() => {
    if (submitting) return;
    setIsAddOpen(false);
    setSubmitError("");
    setFormErrors({});
    setNewSupplier(EMPTY_SUPPLIER);
    requestAnimationFrame(() => addButtonRef.current?.focus());
  }, [submitting]);

  useEffect(() => {
    if (!isAddOpen) return undefined;
    requestAnimationFrame(() => {
      const input = document.querySelector('input[name="name"]');
      if (input) input.focus();
    });
    function handleKeyDown(event) {
      if (event.key === "Escape" && !submitting) closeAddForm();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [closeAddForm, isAddOpen, submitting]);

  async function openAddForm() {
    setSuccessMessage("");
    setSubmitError("");
    setFormErrors({});
    setNewSupplier(EMPTY_SUPPLIER);
    setIsAddOpen(true);
  }

  async function handleAddSupplier(event) {
    event.preventDefault();
    const errors = validateSupplier(newSupplier);
    setFormErrors(errors);
    setSubmitError("");
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      await supplierService.create({
        name: newSupplier.name.trim(),
        email: newSupplier.email.trim() || undefined,
        phone: newSupplier.phone.trim() || undefined,
        address: newSupplier.address.trim() || undefined,
      });

      setIsAddOpen(false);
      setNewSupplier(EMPTY_SUPPLIER);
      setFormErrors({});
      setSuccessMessage("Supplier added successfully.");
      const refreshed = await loadSuppliers();
      if (!refreshed) {
        setSuccessMessage(
          "Supplier added successfully, but the list could not refresh. Try Refresh list.",
        );
      }
      requestAnimationFrame(() => addButtonRef.current?.focus());
    } catch (err) {
      setSubmitError(err.message || "Unable to add supplier. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    let isCurrent = true;

    fetchSuppliers().then((result) => {
      if (!isCurrent) return;
      if (result.error) setError(result.error);
      else setSuppliers(result.suppliers);
      setLoading(false);
    });

    return () => {
      isCurrent = false;
    };
  }, []);

  return (
    <div className="suppliers-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">SUPPLIER MANAGEMENT</p>
          <h1>Suppliers</h1>
          <p className="page-description">
            Manage your product suppliers and keep contact details up to date.
          </p>
        </div>
        <button
          ref={addButtonRef}
          className="primary-button"
          onClick={openAddForm}
          type="button"
        >
          <span className="button-plus">+</span>
          Add supplier
        </button>
      </section>

      {successMessage && (
        <div className="success-message" role="status">
          {successMessage}
          <button
            type="button"
            aria-label="Dismiss success message"
            onClick={() => setSuccessMessage("")}
          >
            ×
          </button>
        </div>
      )}

      <section className="stats-grid">
        <article className="stat-card">
          <span className="stat-label">Total suppliers</span>
          <strong>{loading ? "—" : suppliers.length}</strong>
          <span className="stat-note">Suppliers in your network</span>
        </article>
      </section>

      <section className="suppliers-card">
        <div className="suppliers-heading">
          <div>
            <h2>Supplier directory</h2>
            <p>View and manage your suppliers.</p>
          </div>
        </div>

        {error && (
          <div className="error-message" role="alert">
            <strong>Could not load suppliers.</strong>
            <p>{error}</p>
            <button onClick={loadSuppliers}>Try again</button>
          </div>
        )}

        <div className="table-wrapper">
          <table className="suppliers-table">
            <thead>
              <tr>
                <th>Supplier</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Address</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="5" className="table-message">
                    Loading suppliers…
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan="5" className="table-message">
                    Check the error above and retry.
                  </td>
                </tr>
              ) : suppliers.length === 0 ? (
                <tr>
                  <td colSpan="5" className="table-message">
                    No suppliers found. Add your first supplier to get started.
                  </td>
                </tr>
              ) : (
                suppliers.map((supplier) => (
                  <tr key={supplier.id}>
                    <td>
                      <div className="supplier-identity">
                        <span className="supplier-avatar">
                          {supplier.name.charAt(0).toUpperCase()}
                        </span>
                        <div>
                          <strong>{supplier.name}</strong>
                          <span>Supplier #{supplier.id}</span>
                        </div>
                      </div>
                    </td>
                    <td>{supplier.email || "—"}</td>
                    <td>{supplier.phone || "—"}</td>
                    <td>{supplier.address || "—"}</td>
                    <td>
                      <div className="supplier-row-actions"></div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <footer className="suppliers-footer">
          <span>
            Showing {loading ? "…" : suppliers.length} supplier
            {suppliers.length !== 1 ? "s" : ""} in the current result
          </span>
          <button
            className="refresh-button"
            onClick={loadSuppliers}
            disabled={loading}
          >
            Refresh list
          </button>
        </footer>
      </section>

      {isAddOpen && (
        <div className="modal-backdrop">
          <section
            ref={addButtonRef}
            className="supplier-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-supplier-title"
            aria-describedby="add-supplier-description"
          >
            <header className="supplier-modal-header">
              <div>
                <p className="eyebrow">SUPPLIER MANAGEMENT</p>
                <h2 id="add-supplier-title">Add supplier</h2>
                <p id="add-supplier-description">
                  Enter the supplier details to add them to your directory.
                </p>
              </div>
              <button
                className="modal-close-button"
                type="button"
                aria-label="Close add supplier form"
                onClick={closeAddForm}
                disabled={submitting}
              >
                ×
              </button>
            </header>

            <form className="supplier-form" onSubmit={handleAddSupplier} noValidate>
              {submitError && (
                <div className="form-error" role="alert">{submitError}</div>
              )}

              <label className="supplier-form-field" htmlFor="supplier-name">
                <span>Supplier name <span aria-hidden="true">*</span></span>
                <input
                  id="supplier-name"
                  name="name"
                  type="text"
                  value={newSupplier.name}
                  required
                  maxLength={100}
                  aria-invalid={Boolean(formErrors.name)}
                  aria-describedby={formErrors.name ? "supplier-name-error" : undefined}
                  onChange={(event) =>
                    setNewSupplier({ ...newSupplier, name: event.target.value })
                  }
                />
                {formErrors.name && (
                  <small id="supplier-name-error">{formErrors.name}</small>
                )}
              </label>

              <label className="supplier-form-field" htmlFor="supplier-email">
                <span>Email address</span>
                <input
                  id="supplier-email"
                  name="email"
                  type="email"
                  value={newSupplier.email}
                  maxLength={254}
                  aria-invalid={Boolean(formErrors.email)}
                  aria-describedby={formErrors.email ? "supplier-email-error" : undefined}
                  onChange={(event) =>
                    setNewSupplier({ ...newSupplier, email: event.target.value })
                  }
                />
                {formErrors.email && (
                  <small id="supplier-email-error">{formErrors.email}</small>
                )}
              </label>

              <div className="supplier-form-row">
                <label className="supplier-form-field" htmlFor="supplier-phone">
                  <span>Phone number</span>
                  <input
                    id="supplier-phone"
                    name="phone"
                    type="tel"
                    value={newSupplier.phone}
                    maxLength={50}
                    aria-invalid={Boolean(formErrors.phone)}
                    aria-describedby={formErrors.phone ? "supplier-phone-error" : undefined}
                    onChange={(event) =>
                      setNewSupplier({ ...newSupplier, phone: event.target.value })
                    }
                  />
                  {formErrors.phone && (
                    <small id="supplier-phone-error">{formErrors.phone}</small>
                  )}
                </label>

                <label className="supplier-form-field" htmlFor="supplier-address">
                  <span>Address</span>
                  <input
                    id="supplier-address"
                    name="address"
                    type="text"
                    value={newSupplier.address}
                    maxLength={200}
                    aria-invalid={Boolean(formErrors.address)}
                    aria-describedby={formErrors.address ? "supplier-address-error" : undefined}
                    onChange={(event) =>
                      setNewSupplier({ ...newSupplier, address: event.target.value })
                    }
                  />
                  {formErrors.address && (
                    <small id="supplier-address-error">{formErrors.address}</small>
                  )}
                </label>
              </div>

              <footer className="supplier-form-actions">
                <button
                  className="reset-button"
                  type="button"
                  onClick={closeAddForm}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button className="search-button" type="submit" disabled={submitting}>
                  {submitting ? "Adding…" : "Add supplier"}
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
