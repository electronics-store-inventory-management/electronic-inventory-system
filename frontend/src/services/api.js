
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

let accessToken = null;

export function setAccessToken(token) {
  accessToken = token;
}

export async function apiRequest(path, options = {}) {
  const { authenticated = true, ...requestOptions } = options;
  const headers = {
    "Content-Type": "application/json",
    ...requestOptions.headers,
  };
  if (authenticated && accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    headers,
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;

    try {
      const error = await response.json();
      message =
        typeof error.detail === "string"
          ? error.detail
          : JSON.stringify(error.detail ?? error);
    } catch {
      // Keep the default HTTP error message.
    }

    throw new Error(message);
  }

  if (response.status === 204) return null;
  return response.json();
}
