import { getStockStatus, stockStatus } from "../shared/stockStatus.js";

export function summarizeInventory(products) {
  const lowStock = [];
  const outOfStock = [];
  let value = 0;

  for (const product of products) {
    const status = getStockStatus(product);
    if (status === stockStatus.low) lowStock.push(product);
    if (status === stockStatus.out) outOfStock.push(product);
    value += Number(product.price) * Number(product.quantity);
  }

  return { total: products.length, value, lowStock, outOfStock };
}
