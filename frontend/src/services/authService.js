import { apiRequest } from "./api";

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
      result.expires_in <= 0
    ) {
      throw new Error("The sign-in response was not valid.");
    }

    return {
      accessToken: result.access_token,
      tokenType: result.token_type,
      expiresIn: result.expires_in,
    };
  } catch (error) {
    if (error.status === 401) {
      throw new Error("Username or password is incorrect.", { cause: error });
    }
    if (error.status) {
      throw new Error("Unable to sign in right now. Please try again.", { cause: error });
    }
    throw new Error("Unable to connect. Check your connection and try again.", { cause: error });
  }
}
