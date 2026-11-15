import assert from "node:assert/strict";
import test from "node:test";
import { summarizeInventory } from "../src/pages/dashboard/dashboardSummary.js";

test("uses shared stock thresholds and computes actual inventory value", () => {
  const products = [
    { id: 1, quantity: 5, min_stock_level: 5, price: "10.20" },
    { id: 2, quantity: 0, min_stock_level: 5, price: "500" },
    { id: 3, quantity: 6, min_stock_level: 5, price: "5" },
    { id: 4, quantity: 2, min_stock_level: 0, price: "10" },
  ];
  assert.deepEqual(summarizeInventory(products), {
    total: 4, value: 101, lowStock: [products[0]], outOfStock: [products[1]],
  });
});

test("represents an empty catalogue", () => {
  assert.deepEqual(summarizeInventory([]), { total: 0, value: 0, lowStock: [], outOfStock: [] });
});
