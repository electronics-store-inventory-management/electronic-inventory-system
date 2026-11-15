import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { productService } from "../../services/productService";
import { getSessionUser } from "../../services/sessionUser";
import { transactionService } from "../../services/transactionService";
import { sampleProducts } from "../../services/sampleData";
import { Alert, LoadingOrError, PageHeading } from "../shared/WorkspaceTools";
import "../shared/Workspace.css";
import "./TransactionsPage.css";

const EMPTY_TRANSACTION = {
  product_id: "",
  transaction_type: "DEDUCT",
  quantity: "1",
  reference: "",
  date: "",
};

const TYPE_LABELS = {
  ADD: "Stock in",
  DEDUCT: "Stock out",
  SET: "Correction",
};

function validateTransaction(values) {
  const errors = {};
  const quantity = Number(values.quantity);
  const reference = values.reference.trim();

  if (!values.product_id) errors.product_id = "Select a product.";
  if (!TYPE_LABELS[values.transaction_type]) {
    errors.transaction_type = "Select a transaction type.";
  }

  if (!Number.isInteger(quantity) || quantity < 0) {
    errors.quantity = "Enter a whole number of 0 or more.";
  } else if (values.transaction_type !== "SET" && quantity <= 0) {
    errors.quantity = "Quantity must be greater than zero.";
  }

  if (!reference) errors.reference = "Enter a reference.";
  else if (reference.length > 100) {
    errors.reference = "Use 100 characters or fewer.";
  }

  if (values.date && Number.isNaN(new Date(values.date).getTime())) {
    errors.date = "Enter a valid date and time.";
  }

  return errors;
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function quantityLabel(transaction) {
  if (transaction.transaction_type === "ADD") {
    return `+${transaction.quantity}`;
  }
  if (transaction.transaction_type === "DEDUCT") {
    return `−${transaction.quantity}`;
  }
  return `= ${transaction.quantity}`;
}

function newIdempotencyKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `txn-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function TransactionsPage() {
  const currentUser = getSessionUser();
  const isAdmin = currentUser?.role === "admin";

  const [transactions, setTransactions] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [noticeTone, setNoticeTone] = useState("success");

  const [productFilter, setProductFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [referenceFilter, setReferenceFilter] = useState("");

  const [formOpen, setFormOpen] = useState(false);
  const [formValues, setFormValues] = useState(EMPTY_TRANSACTION);
  const [formErrors, setFormErrors] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const firstFieldRef = useRef(null);

  const load = useCallback(async () => {
    await Promise.resolve();
    setLoading(true);
    setError("");
    setNotice("");

    try {
      const [transactionList, productList] = await Promise.all([
        transactionService.list(),
        productService.list().catch(() => sampleProducts),
      ]);
      setTransactions(transactionList);
      setProducts(productList);
    } catch (loadError) {
      setError(loadError.message || "Unable to load transactions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(load, 0);
    return () => clearTimeout(timer);
  }, [load]);

  const closeForm = useCallback(() => {
    if (submitting) return;
    setFormOpen(false);
    setFormValues(EMPTY_TRANSACTION);
    setFormErrors({});
    setSubmitError("");
  }, [submitting]);

  useEffect(() => {
    if (!formOpen) return undefined;

    function handleKeyDown(event) {
      if (event.key === "Escape" && !submitting) closeForm();
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [closeForm, formOpen, submitting]);

  useEffect(() => {
    if (formOpen) firstFieldRef.current?.focus();
  }, [formOpen]);

  const productById = useMemo(
    () => new Map(products.map((product) => [Number(product.id), product])),
    [products],
  );

  const filteredTransactions = useMemo(() => {
    const query = referenceFilter.trim().toLowerCase();

    return transactions.filter((transaction) => {
      if (
        productFilter !== "all" &&
        Number(transaction.product_id) !== Number(productFilter)
      ) {
        return false;
      }
      if (
        typeFilter !== "all" &&
        transaction.transaction_type !== typeFilter
      ) {
        return false;
      }
      if (
        query &&
        !String(transaction.reference || "").toLowerCase().includes(query)
      ) {
        return false;
      }
      return true;
    });
  }, [productFilter, referenceFilter, transactions, typeFilter]);

  const totals = useMemo(() => {
    const added = transactions
      .filter((transaction) => transaction.transaction_type === "ADD")
      .reduce((sum, transaction) => sum + Number(transaction.quantity || 0), 0);
    const deducted = transactions
      .filter((transaction) => transaction.transaction_type === "DEDUCT")
      .reduce((sum, transaction) => sum + Number(transaction.quantity || 0), 0);

    return {
      movements: transactions.length,
      added,
      deducted,
      net: added - deducted,
    };
  }, [transactions]);

  function showNotice(message, tone = "success") {
    setNotice(message);
    setNoticeTone(tone);
  }

  function openForm() {
    if (!products.length) {
      showNotice("Add a product before recording a transaction.", "error");
      return;
    }

    setFormValues({
      ...EMPTY_TRANSACTION,
      product_id: String(products[0].id),
    });
    setFormErrors({});
    setSubmitError("");
    setNotice("");
    setFormOpen(true);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const errors = validateTransaction(formValues);
    setFormErrors(errors);
    setSubmitError("");
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      const payload = {
        product_id: Number(formValues.product_id),
        transaction_type: formValues.transaction_type,
        quantity: Number(formValues.quantity),
        user_id: currentUser?.id || 1,
        reference: formValues.reference.trim(),
      };

      if (formValues.date) {
        payload.date = new Date(formValues.date).toISOString();
      }

      await transactionService.create(payload, newIdempotencyKey());
      setFormOpen(false);
      setFormValues(EMPTY_TRANSACTION);
      setFormErrors({});
      await load();
      showNotice("Transaction recorded successfully.");
    } catch (submitFailure) {
      setSubmitError(
        submitFailure.message ||
          "Unable to record the transaction. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function clearFilters() {
    setProductFilter("all");
    setTypeFilter("all");
    setReferenceFilter("");
  }

  function productName(productId) {
    return (
      productById.get(Number(productId))?.name || `Product #${productId}`
    );
  }

  return (
    <section className="workspace-page transactions-page">
      <PageHeading
        title="Transactions"
        description="Review inventory movements and record stock adjustments."
        action={
          <button className="workspace-button" type="button" onClick={openForm}>
            Record transaction
          </button>
        }
      />

      {notice && (
        <Alert success={noticeTone === "success"}>
          {notice}
          <button
            className="transactions-dismiss"
            type="button"
            aria-label="Dismiss message"
            onClick={() => setNotice("")}
          >
            ×
          </button>
        </Alert>
      )}

      <div className="workspace-stats transactions-stats">
        <div className="workspace-stat">
          <span>Movements</span>
          <strong>{loading ? "—" : totals.movements}</strong>
        </div>
        <div className="workspace-stat">
          <span>Units added</span>
          <strong>{loading ? "—" : totals.added.toLocaleString("en-IN")}</strong>
        </div>
        <div className="workspace-stat">
          <span>Units deducted</span>
          <strong>
            {loading ? "—" : totals.deducted.toLocaleString("en-IN")}
          </strong>
        </div>
        <div className="workspace-stat">
          <span>Net change</span>
          <strong
            className={
              totals.net < 0
                ? "transactions-negative"
                : totals.net > 0
                  ? "transactions-positive"
                  : ""
            }
          >
            {loading
              ? "—"
              : `${totals.net > 0 ? "+" : ""}${totals.net.toLocaleString("en-IN")}`}
          </strong>
        </div>
      </div>

      <div className="workspace-card">
        <div className="workspace-card-head">
          <div>
            <h2>Transaction history</h2>
            <p>Filter by product, transaction type or reference.</p>
          </div>
          <span className="transactions-count">
            {filteredTransactions.length}{" "}
            {filteredTransactions.length === 1 ? "record" : "records"}
          </span>
        </div>

        <div className="transactions-filters">
          <label className="workspace-field">
            <span>Product</span>
            <select
              value={productFilter}
              onChange={(event) => setProductFilter(event.target.value)}
            >
              <option value="all">All products</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </select>
          </label>

          <label className="workspace-field">
            <span>Type</span>
            <select
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value)}
            >
              <option value="all">All types</option>
              <option value="ADD">Stock in</option>
              <option value="DEDUCT">Stock out</option>
              <option value="SET">Correction</option>
            </select>
          </label>

          <label className="workspace-field">
            <span>Reference</span>
            <input
              value={referenceFilter}
              onChange={(event) => setReferenceFilter(event.target.value)}
              placeholder="e.g. PO-2026-1101"
            />
          </label>

          <button
            className="workspace-button secondary"
            type="button"
            onClick={clearFilters}
            disabled={productFilter === "all" && typeFilter === "all" && !referenceFilter}
          >
            Clear
          </button>
          <button
            className="workspace-button secondary"
            type="button"
            onClick={load}
            disabled={loading}
          >
            Refresh
          </button>
        </div>

        <LoadingOrError
          loading={loading}
          error={error}
          empty={
            !filteredTransactions.length
              ? transactions.length
                ? "No transactions match these filters."
                : "No transactions recorded yet."
              : ""
          }
          onRetry={load}
        />

        {!loading && !error && filteredTransactions.length > 0 && (
          <div className="workspace-table-wrap">
            <table className="workspace-table transactions-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Reference</th>
                  <th>Product</th>
                  <th>Type</th>
                  <th>Quantity</th>
                  <th>Recorded by</th>
                </tr>
              </thead>
              <tbody>
                {filteredTransactions.map((transaction) => (
                  <tr key={transaction.id}>
                    <td>{formatDate(transaction.date)}</td>
                    <td>
                      <div className="transactions-reference">
                        <strong>{transaction.reference}</strong>
                        <span>
                          TXN-{String(transaction.id).padStart(4, "0")}
                        </span>
                      </div>
                    </td>
                    <td>{productName(transaction.product_id)}</td>
                    <td>
                      <span
                        className={`transactions-type-badge transactions-type-${transaction.transaction_type.toLowerCase()}`}
                      >
                        {TYPE_LABELS[transaction.transaction_type] ||
                          transaction.transaction_type}
                      </span>
                    </td>
                    <td
                      className={`transactions-quantity transactions-quantity-${transaction.transaction_type.toLowerCase()}`}
                    >
                      {quantityLabel(transaction)}
                    </td>
                    <td>User #{transaction.user_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <footer className="transactions-footer">
          <span>
            Showing {loading ? "…" : filteredTransactions.length} of{" "}
            {transactions.length} transactions
          </span>
          <span>
            {totals.movements} total movements · net {totals.net > 0 ? "+" : ""}
            {totals.net.toLocaleString("en-IN")} units
          </span>
        </footer>
      </div>

      {formOpen && (
        <div className="workspace-modal-backdrop">
          <section
            className="workspace-modal transactions-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="transaction-form-title"
          >
            <div className="transactions-modal-head">
              <div>
                <p className="eyebrow">INVENTORY MOVEMENT</p>
                <h2 id="transaction-form-title">Record transaction</h2>
                <p>
                  Signed in as {currentUser?.username || "user"} · User #
                  {currentUser?.id || "—"}
                </p>
              </div>
              <button
                className="workspace-button secondary"
                type="button"
                onClick={closeForm}
                disabled={submitting}
              >
                Close
              </button>
            </div>

            {!isAdmin && (
              <div className="workspace-alert transactions-role-note">
                Only administrators can record stock in (ADD) or stock
                corrections (SET). Your account can record stock out (DEDUCT)
                transactions.
              </div>
            )}

            <form
              className="transactions-form"
              onSubmit={handleSubmit}
              noValidate
            >
              {submitError && (
                <div className="workspace-alert" role="alert">
                  {submitError}
                </div>
              )}

              <div className="transactions-form-row">
                <label className="transactions-field">
                  <span>Product *</span>
                  <select
                    ref={firstFieldRef}
                    value={formValues.product_id}
                    required
                    aria-invalid={Boolean(formErrors.product_id)}
                    onChange={(event) =>
                      setFormValues({
                        ...formValues,
                        product_id: event.target.value,
                      })
                    }
                  >
                    <option value="">Select a product</option>
                    {products.map((product) => (
                      <option key={product.id} value={product.id}>
                        {product.name} · {product.quantity} in stock
                      </option>
                    ))}
                  </select>
                  {formErrors.product_id && (
                    <small className="transactions-field-error">
                      {formErrors.product_id}
                    </small>
                  )}
                </label>

                <label className="transactions-field">
                  <span>Type *</span>
                  <select
                    value={formValues.transaction_type}
                    required
                    aria-invalid={Boolean(formErrors.transaction_type)}
                    onChange={(event) =>
                      setFormValues({
                        ...formValues,
                        transaction_type: event.target.value,
                      })
                    }
                  >
                    <option value="DEDUCT">Stock out (DEDUCT)</option>
                    <option value="ADD" disabled={!isAdmin}>
                      Stock in (ADD)
                    </option>
                    <option value="SET" disabled={!isAdmin}>
                      Stock correction (SET)
                    </option>
                  </select>
                  {formErrors.transaction_type && (
                    <small className="transactions-field-error">
                      {formErrors.transaction_type}
                    </small>
                  )}
                </label>
              </div>

              <div className="transactions-form-row">
                <label className="transactions-field">
                  <span>Quantity *</span>
                  <input
                    type="number"
                    min={formValues.transaction_type === "SET" ? 0 : 1}
                    step={1}
                    value={formValues.quantity}
                    required
                    aria-invalid={Boolean(formErrors.quantity)}
                    onChange={(event) =>
                      setFormValues({
                        ...formValues,
                        quantity: event.target.value,
                      })
                    }
                  />
                  {formErrors.quantity && (
                    <small className="transactions-field-error">
                      {formErrors.quantity}
                    </small>
                  )}
                </label>

                <label className="transactions-field">
                  <span>Reference *</span>
                  <input
                    value={formValues.reference}
                    maxLength={100}
                    required
                    placeholder="e.g. PO-2026-1106"
                    aria-invalid={Boolean(formErrors.reference)}
                    onChange={(event) =>
                      setFormValues({
                        ...formValues,
                        reference: event.target.value,
                      })
                    }
                  />
                  {formErrors.reference && (
                    <small className="transactions-field-error">
                      {formErrors.reference}
                    </small>
                  )}
                </label>
              </div>

              <label className="transactions-field">
                <span>Date and time</span>
                <input
                  type="datetime-local"
                  value={formValues.date}
                  aria-invalid={Boolean(formErrors.date)}
                  onChange={(event) =>
                    setFormValues({
                      ...formValues,
                      date: event.target.value,
                    })
                  }
                />
                {formErrors.date ? (
                  <small className="transactions-field-error">
                    {formErrors.date}
                  </small>
                ) : (
                  <small className="transactions-help">
                    Leave blank to use the current server time.
                  </small>
                )}
              </label>

              <p className="transactions-help">
                Each submission includes an idempotency key so refreshing the
                request will not create duplicate movements.
              </p>

              <footer className="transactions-form-actions">
                <button
                  className="workspace-button secondary"
                  type="button"
                  onClick={closeForm}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button
                  className="workspace-button"
                  type="submit"
                  disabled={submitting}
                >
                  {submitting ? "Recording…" : "Record transaction"}
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}
    </section>
  );
}