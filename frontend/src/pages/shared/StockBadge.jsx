import { getStockStatus } from "./stockStatus";

export default function StockBadge({ product, className }) {
  const { label, tone } = getStockStatus(product);
  return <span className={`ui-badge ${className} ui-tone-${tone}`}>{label}</span>;
}
