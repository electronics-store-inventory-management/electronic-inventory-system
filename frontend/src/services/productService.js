
import { apiRequest } from "./api";

export const productService = {
  list: (filters = {}) => {
    const params = new URLSearchParams();

    if (filters.name?.trim()) {
      params.set("name", filters.name.trim());
    }

    if (filters.category?.trim()) {
      params.set("category", filters.category.trim());
    }

    if (filters.product_id) {
      params.set("product_id", filters.product_id);
    }

    const query = params.toString();
    return apiRequest(`/products/${query ? `?${query}` : ""}`);
  },

  get: (id) => apiRequest(`/products/${id}`),

  create: (product) =>
    apiRequest("/products/", {
      method: "POST",
      body: JSON.stringify(product),
    }),

  update: (id, product) =>
    apiRequest(`/products/${id}`, {
      method: "PUT",
      body: JSON.stringify(product),
    }),

  remove: (id) =>
    apiRequest(`/products/${id}`, {
      method: "DELETE",
    }),
};
