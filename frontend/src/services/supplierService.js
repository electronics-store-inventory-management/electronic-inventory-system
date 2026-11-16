
import { apiRequest } from "./api";

export const supplierService = {
  list: () => apiRequest("/suppliers/"),
  create: (supplier) =>
    apiRequest("/suppliers/", {
      method: "POST",
      body: JSON.stringify(supplier),
    }),
  update: (id, supplier) =>
    apiRequest(`/suppliers/${id}`, {
      method: "PUT",
      body: JSON.stringify(supplier),
    }),
};
