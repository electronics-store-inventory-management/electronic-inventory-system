import { Link } from "react-router-dom";
import { inventoryService } from "../../services/inventoryService";
import { transactionService } from "../../services/transactionService";
import StockBadge from "../shared/StockBadge";
import { useLoad } from "../shared/useLoad";
import {
  LoadingOrError, PageHeading, RefreshButton, WorkspaceCard, WorkspaceState, WorkspaceStats, WorkspaceTable,
} from "../shared/WorkspaceTools";
import { summarizeInventory } from "./dashboardSummary";

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });
const date = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });
const action = { ADD: "Stock added", DEDUCT: "Stock deducted", SET: "Stock set" };

export default function DashboardPage() {
  const inventory = useLoad(inventoryService.listProducts);
  const activity = useLoad(transactionService.recent);
  const { total, value, lowStock, outOfStock } = summarizeInventory(inventory.data);
  const attention = [...outOfStock, ...lowStock].slice(0, 5);
  const names = new Map(inventory.data.map((product) => [product.id, product.name]));
  const stats = [
    { title: "Products tracked", value: total, icon: "products", tone: "info" },
    { title: "Inventory value", value: currency.format(value), icon: "value", tone: "success" },
    { title: "Low stock", value: lowStock.length, icon: "warning", tone: "warning" },
    { title: "Out of stock", value: outOfStock.length, icon: "inventory", tone: "error" },
  ];

  function refresh() {
    inventory.refresh();
    activity.refresh();
  }

  return (
    <div className="workspace-page">
      <PageHeading title="Dashboard" description="Review catalogue health and recent stock activity."
        action={<RefreshButton onClick={refresh}>Refresh dashboard</RefreshButton>} />
      <WorkspaceStats label="Dashboard inventory summary" metrics={stats} loading={inventory.loading} error={inventory.error} />
      <div className="workspace-report-grid">
        <WorkspaceCard id="dashboard-stock" title="Stock to review"
          detail={<Link className="ui-button ui-button--secondary" to="/inventory">View inventory</Link>}>
          <LoadingOrError loading={inventory.loading} error={inventory.error} loadingTitle="Loading stock…"
            errorTitle="Could not load stock" onRetry={inventory.refresh} />
          {!inventory.loading && !inventory.error && (attention.length ? (
            <WorkspaceTable label="Products with low or no stock">
              <thead><tr><th scope="col">Product</th><th scope="col" className="workspace-number">Available</th><th scope="col">Status</th></tr></thead>
              <tbody>
                {attention.map((product) => (
                  <tr key={product.id}>
                    <th scope="row">{product.name}</th>
                    <td className="workspace-number">{product.quantity}</td>
                    <td><StockBadge product={product} className="workspace-stock-status" /></td>
                  </tr>
                ))}
              </tbody>
            </WorkspaceTable>
          ) : <WorkspaceState title={total ? "No stock alerts" : "No products yet"}
            description={total ? "No listed product is low or out of stock." : "Catalogue items will appear here when an admin adds them."}
            icon={total ? "check" : "products"} tone={total ? "success" : "info"} />)}
        </WorkspaceCard>
        <WorkspaceCard id="dashboard-activity" title="Recent stock activity">
          <LoadingOrError loading={activity.loading} error={activity.error} loadingTitle="Loading activity…"
            errorTitle="Could not load stock activity" onRetry={activity.refresh} />
          {!activity.loading && !activity.error && (activity.data.length ? (
            <WorkspaceTable label="Recent inventory transactions">
              <thead><tr><th scope="col">Product</th><th scope="col">Action</th><th scope="col" className="workspace-number">Units</th><th scope="col">Date</th></tr></thead>
              <tbody>
                {activity.data.map((transaction) => (
                  <tr key={transaction.id}>
                    <th scope="row">{names.get(transaction.product_id) ?? `Product #${transaction.product_id}`}</th>
                    <td>{action[transaction.transaction_type]}</td>
                    <td className="workspace-number">{transaction.quantity}</td>
                    <td><time dateTime={transaction.date}>{date.format(new Date(transaction.date))}</time></td>
                  </tr>
                ))}
              </tbody>
            </WorkspaceTable>
          ) : <WorkspaceState title="No stock transactions yet"
            description="Stock additions, deductions, and adjustments will appear here." icon="transactions" />)}
        </WorkspaceCard>
      </div>
    </div>
  );
}
