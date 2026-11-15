import { apiRequest } from "./api";
import { isOfflineError } from "./sessionUser";
import { sampleTransactions } from "./sampleData";

export const transactionService = {
  async list(filters = {}) {
    const params = new URLSearchParams();
    if (filters.product_id) params.set("product_id", filters.product_id);
    const query = params.toString();

    try {
      return await apiRequest(`/transactions/${query ? `?${query}` : ""}`);
    } catch (error) {
      if (isOfflineError(error)) {
        return filters.product_id
          ? sampleTransactions.filter(
              (transaction) =>
                transaction.product_id === Number(filters.product_id),
            )
          : sampleTransactions;
      }
      throw error;
    }
  },

  create(transaction, idempotencyKey) {
    return apiRequest("/transactions/", {
      method: "POST",
      headers: idempotencyKey
        ? { "Idempotency-Key": idempotencyKey }
        : undefined,
      body: JSON.stringify(transaction),
    });
  },
};