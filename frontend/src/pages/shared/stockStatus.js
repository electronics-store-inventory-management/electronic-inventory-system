export const stockStatus = {
  out: { label: "Out of stock", tone: "error" },
  low: { label: "Low stock", tone: "warning" },
  inStock: { label: "In stock", tone: "success" },
  unmonitored: { label: "No minimum set", tone: "info" },
};

export function getStockStatus(product) {
  const quantity = Number(product.quantity);
  const minimum = Number(product.min_stock_level ?? 0);

  if (quantity === 0) return stockStatus.out;
  if (minimum === 0) return stockStatus.unmonitored;
  return quantity <= minimum ? stockStatus.low : stockStatus.inStock;
}
