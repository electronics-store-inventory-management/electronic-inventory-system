import { apiRequest } from "./api";

export async function getAccount({ accessToken, signal } = {}) {
  const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined;
  const account = await apiRequest("/auth/me", { headers, signal });
  if (!account || typeof account.username !== "string" || !["admin", "employee"].includes(account.role)) {
    throw new Error("The account response was not valid.");
  }
  return account;
}

export async function register(username, password) {
  try {
    await apiRequest("/auth/register", { method: "POST", body: JSON.stringify({ username, password }) });
  } catch (error) {
    if (error.status === 403) throw new Error("Public signup is currently unavailable.", { cause: error });
    if (error.status) throw error;
    throw new Error("Unable to connect. Check your connection and try again.", { cause: error });
  }
}

export async function login(username, password) {
  try {
    const result = await apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });

    if (
      !result?.access_token ||
      result.token_type?.toLowerCase() !== "bearer" ||
      !Number.isFinite(result.expires_in) ||
      result.expires_in <= 0 ||
      !["admin", "employee"].includes(result.user?.role)
    ) {
      throw new Error("The sign-in response was not valid.");
    }

    return {
      accessToken: result.access_token,
      tokenType: result.token_type,
      expiresIn: result.expires_in,
      role: result.user.role,
    };
  } catch (error) {
    if (error.status === 401) {
      throw new Error("Username or password is incorrect.", { cause: error });
    }
    if (error.status === 429) throw error;
    if (error.status) {
      throw new Error("Unable to sign in right now. Please try again.", { cause: error });
    }
    throw new Error("Unable to connect. Check your connection and try again.", { cause: error });
  }
}
