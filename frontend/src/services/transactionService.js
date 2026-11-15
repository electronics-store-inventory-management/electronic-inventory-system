import { apiRequest } from "./api";

export const transactionService = {
  recent: () => apiRequest("/transactions/?limit=5"),
};
