
import { useCallback, useEffect, useState } from "react";
import { productService } from "../../services/productService";
import "./ProductsPage.css";

export default function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadProducts = useCallback(async (filters = {}) => {
    setLoading(true);
    setError("");

    try {
      const data = await productService.list(filters);
      setProducts(data);
    } catch (err) {
      setError(err.message || "Unable to load products.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

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
          className="primary-button"
          onClick={() =>
            window.alert("The Add Product form is coming in the next step.")
          }
        >
          <span className="button-plus">+</span>
          Add product
        </button>
      </section>

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
    </div>
  );
}
