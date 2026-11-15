import { useMemo } from "react";
import { inventoryService } from "../../services/inventoryService";
import StockBadge from "../shared/StockBadge";
import { useLoad } from "../shared/useLoad";
import { getStockStatus, stockStatus } from "../shared/stockStatus";
import {
  LoadingOrError,
  PageHeading,
  RefreshButton,
  WorkspaceCard,
  WorkspaceState,
  WorkspaceStats,
  WorkspaceTable,
} from "../shared/WorkspaceTools";

export default function InventoryPage() {
  const { data: products, loading, error, refresh } = useLoad(inventoryService.listProducts);
  const low = useMemo(
    () => products.filter((product) => getStockStatus(product) === stockStatus.low),
    [products],
  );
  const units = products.reduce((sum, product) => sum + (+product.quantity || 0), 0);
  const value = products.reduce((sum, product) => sum + (+product.price || 0) * (+product.quantity || 0), 0);
  const metrics = [
    { title: "Products tracked", value: products.length, icon: "products", tone: "info" },
    { title: "Total units", value: units.toLocaleString(), icon: "inventory", tone: "success" },
    { title: "Low-stock items", value: low.length, icon: "warning", tone: "warning" },
  ];

  return (
    <div className="workspace-page">
      <PageHeading
        title="Inventory"
        description="Monitor available stock, reorder thresholds and inventory value."
        action={<RefreshButton onClick={refresh}>Refresh</RefreshButton>}
      />
      <WorkspaceStats label="Inventory summary" metrics={metrics} loading={loading} error={error} />
      <WorkspaceCard
        id="stock-overview"
        title="Stock overview"
        detail={
          <div className="workspace-card-value">
            <span>Inventory value</span>
            <strong>{loading || error ? "—" : `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`}</strong>
          </div>
        }
      >
        <LoadingOrError
          loading={loading}
          error={error}
          loadingTitle="Loading inventory…"
          errorTitle="Could not load inventory"
          onRetry={refresh}
        />
        {!loading && !error && (
          products.length === 0 ? (
            <WorkspaceState
              title="No products in inventory"
              description="Stock levels will appear here when products are added to the catalogue."
              icon="inventory"
            />
          ) : (
            <WorkspaceTable label="Stock overview table" wide>
              <thead>
                <tr>
                  <th scope="col">Product</th>
                  <th scope="col">Category</th>
                  <th scope="col" className="workspace-number">Available</th>
                  <th scope="col" className="workspace-number">Minimum</th>
                  <th scope="col" className="workspace-number">Unit price</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {products.map((product) => {
                  const quantity = +product.quantity;
                  const minimum = +product.min_stock_level;

                  return (
                    <tr key={product.id}>
                      <th scope="row">
                        {product.name}
                        <small className="workspace-product-id">#{product.id}</small>
                      </th>
                      <td><span className="ui-badge workspace-category">{product.category}</span></td>
                      <td className="workspace-number">{quantity}</td>
                      <td className="workspace-number">{minimum}</td>
                      <td className="workspace-number">₹{(+product.price).toLocaleString("en-IN")}</td>
                      <td><StockBadge product={product} className="workspace-stock-status" /></td>
                    </tr>
                  );
                })}
              </tbody>
            </WorkspaceTable>
          )
        )}
      </WorkspaceCard>
    </div>
  );
}
