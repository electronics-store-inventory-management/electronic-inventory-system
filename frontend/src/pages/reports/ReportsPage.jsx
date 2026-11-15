import { reportService } from "../../services/reportService";
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

export default function ReportsPage() {
  const { data: report, loading, error, refresh } = useLoad(reportService.inventory);
  const products = report.products || [];
  // The API subset applies a strict below-minimum cutoff. Use the full list for
  // the UI rule, which includes items exactly at their minimum.
  const low = products.filter((product) => getStockStatus(product) === stockStatus.low);
  const replenishment = products.filter((product) => {
    const status = getStockStatus(product);
    return status === stockStatus.low || (status === stockStatus.out && product.min_stock_level > 0);
  });
  const units = products.reduce((sum, product) => sum + (+product.quantity || 0), 0);
  const metrics = [
    { title: "Total products", value: products.length, icon: "products", tone: "info" },
    { title: "Total units", value: units.toLocaleString(), icon: "inventory", tone: "success" },
    { title: "Low-stock products", value: low.length, icon: "warning", tone: "warning" },
  ];

  return (
    <div className="workspace-page">
      <PageHeading
        title="Reports"
        description="Review inventory levels and products requiring replenishment."
        action={<RefreshButton onClick={refresh}>Refresh report</RefreshButton>}
      />
      <WorkspaceStats label="Inventory report summary" metrics={metrics} loading={loading} error={error} />
      {loading || error ? (
        <WorkspaceCard id="report-status" title="Inventory report">
          <LoadingOrError
            loading={loading}
            error={error}
            loadingTitle="Loading inventory report…"
            errorTitle="Could not load the report"
            onRetry={refresh}
          />
        </WorkspaceCard>
      ) : (
        <div className="workspace-report-grid">
          <WorkspaceCard
            id="low-stock-report"
            title="Replenishment report"
            detail={
              <span className={`ui-badge ${replenishment.length ? "ui-tone-warning" : "ui-tone-success"}`}>
                {replenishment.length} {replenishment.length === 1 ? "item" : "items"}
              </span>
            }
          >
            {replenishment.length === 0 ? (
              <WorkspaceState
                title="No items at their replenishment threshold"
                description="Products with a minimum set appear here when stock reaches that level or falls below it."
                icon={products.length ? "check" : "inventory"}
                tone={products.length ? "success" : "info"}
              />
            ) : (
              <WorkspaceTable label="Replenishment table">
                <thead>
                  <tr>
                    <th scope="col">Product</th>
                    <th scope="col" className="workspace-number">Available</th>
                    <th scope="col" className="workspace-number">Minimum level</th>
                    <th scope="col" className="workspace-number">Shortfall</th>
                  </tr>
                </thead>
                <tbody>
                  {replenishment.map((product) => (
                    <tr key={product.id}>
                      <th scope="row">
                        {product.name}
                        <small className="workspace-product-id">#{product.id}</small>
                        <StockBadge product={product} className="workspace-stock-status" />
                      </th>
                      <td className="workspace-number">{product.quantity}</td>
                      <td className="workspace-number">{product.min_stock_level}</td>
                      <td className="workspace-number">
                        <span className="ui-badge ui-tone-warning">{Math.max(0, product.min_stock_level - product.quantity)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </WorkspaceTable>
            )}
          </WorkspaceCard>

          <WorkspaceCard id="all-inventory-items" title="All inventory items">
            {products.length === 0 ? (
              <WorkspaceState
                title="No inventory items to report"
                description="Products will appear here when the catalogue has inventory records."
                icon="reports"
              />
            ) : (
              <WorkspaceTable label="All inventory items table">
                <thead>
                  <tr>
                    <th scope="col">Product</th>
                    <th scope="col" className="workspace-number">Quantity</th>
                    <th scope="col" className="workspace-number">Minimum level</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((product) => (
                    <tr key={product.id}>
                      <th scope="row">{product.name}</th>
                      <td className="workspace-number">{product.quantity}</td>
                      <td className="workspace-number">{product.min_stock_level}</td>
                      <td><StockBadge product={product} className="workspace-stock-status" /></td>
                    </tr>
                  ))}
                </tbody>
              </WorkspaceTable>
            )}
          </WorkspaceCard>
        </div>
      )}
    </div>
  );
}
