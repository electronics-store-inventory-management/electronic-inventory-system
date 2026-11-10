import { AUTH_SESSION_KEY } from "../auth/session";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function readStoredSession() {
  try {
    return JSON.parse(window.sessionStorage.getItem(AUTH_SESSION_KEY) || "null");
  } catch {
    return null;
  }
}

function clearSessionIfCurrent(accessToken, sessionId) {
  if (!accessToken) return false;

  const currentSession = readStoredSession();
  if (
    currentSession?.accessToken !== accessToken ||
    (currentSession?.sessionId || null) !== sessionId
  ) {
    return false;
  }

  window.sessionStorage.removeItem(AUTH_SESSION_KEY);
  window.dispatchEvent(
    new CustomEvent("auth:unauthorized", {
      detail: { accessToken, sessionId },
    }),
  );
  return true;
}

function getExpectedErrorDetail(status, detail) {
  if (![400, 404, 409, 422].includes(status)) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg)
      .filter((message) => typeof message === "string")
      .join(". ");
  }
  return "";
}

export async function apiRequest(path, options = {}) {
  const isLoginRequest = path === "/auth/login";
  const session = isLoginRequest ? null : readStoredSession();
  const requestToken = session?.accessToken || null;
  const requestSessionId = session?.sessionId || null;
  const tokenExpired = Boolean(
    requestToken &&
      (!Number.isFinite(session.expiresAt) || session.expiresAt <= Date.now()),
  );
  const headers = new Headers(options.headers || {});
  if (isLoginRequest) headers.delete("Authorization");
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (!isLoginRequest && requestToken && !tokenExpired) {
    headers.set("Authorization", `Bearer ${requestToken}`);
  } else if (tokenExpired) {
    clearSessionIfCurrent(requestToken, requestSessionId);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = "";
    try {
      const error = await response.json();
      detail = getExpectedErrorDetail(response.status, error.detail);
    } catch {
      // Use a safe generic message for non-JSON error responses.
    }

    const error = new Error(
      response.status === 403
        ? "You do not have permission to perform this action."
        : detail ||
          (response.status >= 500
            ? "The server could not complete your request. Please try again."
            : `Request failed (${response.status})`),
    );
    error.status = response.status;

    if (response.status === 401 && !isLoginRequest) {
      clearSessionIfCurrent(requestToken, requestSessionId);
    }
    throw error;
  }

  if (response.status === 204) return null;
  return response.json();
}
