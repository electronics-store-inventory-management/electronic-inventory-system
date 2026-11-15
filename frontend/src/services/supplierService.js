
import { apiRequest } from "./api";

export const supplierService = {
  list: () => apiRequest("/suppliers/"),
  create: (supplier) =>
    apiRequest("/suppliers/", {
      method: "POST",
      body: JSON.stringify(supplier),
    }),
};
