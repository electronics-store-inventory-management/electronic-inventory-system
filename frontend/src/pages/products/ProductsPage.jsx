
import { useCallback, useEffect, useRef, useState } from "react";
import { productService } from "../../services/productService";
import "./ProductsPage.css";

const EMPTY_PRODUCT = { name: "", category: "", price: "", quantity: "0" };

function validateProduct(product) {
  const errors = {};
  const name = product.name.trim();
  const category = product.category.trim();

  if (!name) errors.name = "Enter a product name.";
  else if (name.length > 100) errors.name = "Use 100 characters or fewer.";

  if (!category) errors.category = "Enter a category.";
  else if (category.length > 100) {
    errors.category = "Use 100 characters or fewer.";
  }

  const price = product.price.trim();
  const normalizedPrice = price.replace(/^0+(?=\d)/, "");
  if (!/^\d+(?:\.\d{1,2})?$/.test(price)) {
    errors.price = "Enter a positive price with up to 2 decimal places.";
  } else if (normalizedPrice.replace(".", "").length > 10) {
    errors.price = "Price must have no more than 10 digits.";
  } else if (Number(price) <= 0) {
    errors.price = "Price must be greater than 0.";
  }

  const quantity = product.quantity.trim();
  if (!/^\d+$/.test(quantity) || !Number.isSafeInteger(Number(quantity))) {
    errors.quantity = "Enter a whole number quantity of 0 or more.";
  }

  return errors;
}

async function fetchProducts(filters = {}) {
  try {
    return { products: await productService.list(filters), error: "" };
  } catch (err) {
    return {
      products: null,
      error: err.message || "Unable to load products.",
    };
  }
}

export default function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [newProduct, setNewProduct] = useState(EMPTY_PRODUCT);
  const [formErrors, setFormErrors] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const addButtonRef = useRef(null);
  const modalRef = useRef(null);
  const nameInputRef = useRef(null);

  const loadProducts = useCallback(async (filters = {}) => {
    setLoading(true);
    setError("");

    const result = await fetchProducts(filters);
    if (result.error) setError(result.error);
    else setProducts(result.products);
    setLoading(false);
    return !result.error;
  }, []);

  const closeAddForm = useCallback(() => {
    if (submitting) return;
    setIsAddOpen(false);
    setSubmitError("");
    setFormErrors({});
    setNewProduct(EMPTY_PRODUCT);
    requestAnimationFrame(() => addButtonRef.current?.focus());
  }, [submitting]);

  useEffect(() => {
    if (!isAddOpen) return undefined;
    nameInputRef.current?.focus();

    function handleKeyDown(event) {
      if (event.key === "Escape" && !submitting) closeAddForm();
      if (event.key === "Tab") {
        const focusable = modalRef.current?.querySelectorAll(
          'button:not([disabled]), input:not([disabled])',
        );
        if (!focusable?.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [closeAddForm, isAddOpen, submitting]);

  function openAddForm() {
    setSuccessMessage("");
    setSubmitError("");
    setFormErrors({});
    setNewProduct(EMPTY_PRODUCT);
    setIsAddOpen(true);
  }

  async function handleAddProduct(event) {
    event.preventDefault();
    const errors = validateProduct(newProduct);
    setFormErrors(errors);
    setSubmitError("");
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      await productService.create({
        name: newProduct.name.trim(),
        category: newProduct.category.trim(),
        price: newProduct.price.trim(),
        quantity: Number(newProduct.quantity),
      });

      setIsAddOpen(false);
      setNewProduct(EMPTY_PRODUCT);
      setFormErrors({});
      setSearch("");
      setCategory("");
      setSuccessMessage("Product added successfully.");
      const refreshed = await loadProducts();
      if (!refreshed) {
        setSuccessMessage(
          "Product added successfully, but the catalogue could not refresh. Try Refresh list.",
        );
      }
      requestAnimationFrame(() => addButtonRef.current?.focus());
    } catch (err) {
      setSubmitError(err.message || "Unable to add product. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    let isCurrent = true;

    fetchProducts().then((result) => {
      if (!isCurrent) return;
      if (result.error) setError(result.error);
      else setProducts(result.products);
      setLoading(false);
    });

    return () => {
      isCurrent = false;
    };
  }, []);

  function handleSearch(event) {
    event.preventDefault();
    loadProducts({ name: search, category });
  }

  function clearSearch() {
    setSearch("");
    setCategory("");
    loadProducts();
  }

  const totalUnits = products.reduce(
    (sum, product) => sum + product.quantity,
    0,
  );

  const inventoryValue = products.reduce(
    (sum, product) => sum + Number(product.price) * product.quantity,
    0,
  );

  return (
    <div className="products-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">CATALOGUE MANAGEMENT</p>
          <h1>Products</h1>
          <p className="page-description">
            Manage your electronic products and keep your catalogue up to date.
          </p>
        </div>
        <button
          ref={addButtonRef}
          className="primary-button"
          onClick={openAddForm}
          type="button"
        >
          <span className="button-plus">+</span>
          Add product
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
          <span className="stat-label">Products found</span>
          <strong>{loading ? "—" : products.length}</strong>
          <span className="stat-note">In the current result</span>
        </article>

        <article className="stat-card">
          <span className="stat-label">Units in results</span>
          <strong>
            {loading ? "—" : totalUnits.toLocaleString("en-IN")}
          </strong>
          <span className="stat-note">Combined product quantity</span>
        </article>

        <article className="stat-card">
          <span className="stat-label">Stock value in results</span>
          <strong>
            {loading
              ? "—"
              : inventoryValue.toLocaleString("en-IN", {
                  style: "currency",
                  currency: "INR",
                  maximumFractionDigits: 2,
                })}
          </strong>
          <span className="stat-note">Price × quantity</span>
        </article>
      </section>

      <section className="catalogue-card">
        <div className="catalogue-heading">
          <div>
            <h2>Product catalogue</h2>
            <p>Search by product name or category.</p>
          </div>
          <span className="catalogue-count">
            {products.length} {products.length === 1 ? "item" : "items"}
          </span>
        </div>

        <form className="search-form" onSubmit={handleSearch}>
          <label className="search-field">
            <span>Product name</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="e.g. Wireless headphones"
            />
          </label>

          <label className="search-field">
            <span>Category</span>
            <input
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              placeholder="e.g. Audio"
            />
          </label>

          <button className="search-button" type="submit">
            Search
          </button>

          <button
            className="reset-button"
            type="button"
            onClick={clearSearch}
          >
            Clear
          </button>
        </form>

        {error && (
          <div className="error-message" role="alert">
            <strong>Could not load products.</strong>
            <p>{error}</p>
            <button onClick={() => loadProducts({ name: search, category })}>
              Try again
            </button>
          </div>
        )}

        <div className="table-wrapper">
          <table className="products-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Category</th>
                <th>Unit price</th>
                <th>Quantity</th>
                <th>Stock status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="6" className="table-message">
                    Loading products…
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan="6" className="table-message">
                    Check the error above and retry.
                  </td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan="6" className="table-message">
                    No products found. Try another search.
                  </td>
                </tr>
              ) : (
                products.map((product) => (
                  <tr key={product.id}>
                    <td>
                      <div className="product-identity">
                        <span className="product-avatar">
                          {product.name.charAt(0).toUpperCase()}
                        </span>
                        <div>
                          <strong>{product.name}</strong>
                          <span>PRD-{String(product.id).padStart(4, "0")}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="category-chip">{product.category}</span>
                    </td>
                    <td className="price-cell">
                      {Number(product.price).toLocaleString("en-IN", {
                        style: "currency",
                        currency: "INR",
                      })}
                    </td>
                    <td>{product.quantity}</td>
                    <td>
                      <span
                        className={`stock-badge ${
                          product.quantity === 0
                            ? "out-of-stock"
                            : product.quantity <= 5
                              ? "low-stock"
                              : "in-stock"
                        }`}
                      >
                        {product.quantity === 0
                          ? "Out of stock"
                          : product.quantity <= 5
                            ? "Low stock"
                            : "In stock"}
                      </span>
                    </td>
                    <td>
                      <span className="action-placeholder">
                        Actions coming next
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <footer className="catalogue-footer">
          <span>
            Showing {loading ? "…" : products.length} products in the current
            result
          </span>
          <button
            className="refresh-button"
            onClick={() => loadProducts({ name: search, category })}
            disabled={loading}
          >
            Refresh list
          </button>
        </footer>
      </section>

      {isAddOpen && (
        <div className="modal-backdrop">
          <section
            ref={modalRef}
            className="product-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-product-title"
            aria-describedby="add-product-description"
          >
            <header className="product-modal-header">
              <div>
                <p className="eyebrow">PRODUCT CATALOGUE</p>
                <h2 id="add-product-title">Add product</h2>
                <p id="add-product-description">
                  Enter the product details to add it to your inventory.
                </p>
              </div>
              <button
                className="modal-close-button"
                type="button"
                aria-label="Close add product form"
                onClick={closeAddForm}
                disabled={submitting}
              >
                ×
              </button>
            </header>

            <form className="product-form" onSubmit={handleAddProduct} noValidate>
              {submitError && (
                <div className="form-error" role="alert">
                  {submitError}
                </div>
              )}
              <label className="product-form-field" htmlFor="product-name">
                <span>Product name <span aria-hidden="true">*</span></span>
                <input
                  ref={nameInputRef}
                  id="product-name"
                  name="name"
                  type="text"
                  value={newProduct.name}
                  required
                  maxLength={100}
                  aria-invalid={Boolean(formErrors.name)}
                  aria-describedby={formErrors.name ? "product-name-error" : undefined}
                  onChange={(event) =>
                    setNewProduct({ ...newProduct, name: event.target.value })
                  }
                />
                {formErrors.name && <small id="product-name-error">{formErrors.name}</small>}
              </label>

              <label className="product-form-field" htmlFor="product-category">
                <span>Category <span aria-hidden="true">*</span></span>
                <input
                  id="product-category"
                  name="category"
                  type="text"
                  value={newProduct.category}
                  required
                  maxLength={100}
                  aria-invalid={Boolean(formErrors.category)}
                  aria-describedby={formErrors.category ? "product-category-error" : undefined}
                  onChange={(event) =>
                    setNewProduct({ ...newProduct, category: event.target.value })
                  }
                />
                {formErrors.category && <small id="product-category-error">{formErrors.category}</small>}
              </label>

              <div className="product-form-row">
                <label className="product-form-field" htmlFor="product-price">
                  <span>Price (INR) <span aria-hidden="true">*</span></span>
                  <input
                    id="product-price"
                    name="price"
                    type="text"
                    inputMode="decimal"
                    value={newProduct.price}
                    required
                    aria-invalid={Boolean(formErrors.price)}
                    aria-describedby={formErrors.price ? "product-price-help product-price-error" : "product-price-help"}
                    onChange={(event) =>
                      setNewProduct({ ...newProduct, price: event.target.value })
                    }
                  />
                  <small id="product-price-help">Greater than 0, up to 2 decimal places.</small>
                  {formErrors.price && <small id="product-price-error">{formErrors.price}</small>}
                </label>

                <label className="product-form-field" htmlFor="product-quantity">
                  <span>Quantity <span aria-hidden="true">*</span></span>
                  <input
                    id="product-quantity"
                    name="quantity"
                    type="text"
                    inputMode="numeric"
                    value={newProduct.quantity}
                    required
                    aria-invalid={Boolean(formErrors.quantity)}
                    aria-describedby={formErrors.quantity ? "product-quantity-error" : undefined}
                    onChange={(event) =>
                      setNewProduct({ ...newProduct, quantity: event.target.value })
                    }
                  />
                  {formErrors.quantity && <small id="product-quantity-error">{formErrors.quantity}</small>}
                </label>
              </div>

              <footer className="product-form-actions">
                <button
                  className="reset-button"
                  type="button"
                  onClick={closeAddForm}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button className="search-button" type="submit" disabled={submitting}>
                  {submitting ? "Adding…" : "Add product"}
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
