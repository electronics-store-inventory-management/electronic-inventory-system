import { readStoredSession, removeStoredSession } from "../auth/session.js";

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL?.trim().replace(/\/+$/, "") ||
  (import.meta.env?.DEV ? "http://localhost:8000" : "");

function reportUnauthorized(accessToken, sessionId) {
  removeStoredSession(accessToken, sessionId);
  window.dispatchEvent(
    new CustomEvent("auth:unauthorized", {
      detail: { accessToken, sessionId },
    }),
  );
}

function getExpectedErrorDetail(status, detail) {
  if (![400, 404, 409, 422, 429].includes(status)) return "";
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
  const publicAuthRequest = path === "/auth/login" || path === "/auth/register";
  const headers = new Headers(options.headers || {});
  const session = publicAuthRequest || headers.has("Authorization") ? null : readStoredSession();
  const requestToken = session?.accessToken || null;
  const requestSessionId = session?.sessionId || null;
  const tokenExpired = Boolean(
    requestToken &&
      (!Number.isFinite(session.expiresAt) || session.expiresAt <= Date.now()),
  );
  if (publicAuthRequest) headers.delete("Authorization");
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (requestToken && !tokenExpired) {
    headers.set("Authorization", `Bearer ${requestToken}`);
  } else if (tokenExpired) {
    reportUnauthorized(requestToken, requestSessionId);
    throw Object.assign(new Error("Your session has expired."), { status: 401 });
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

    if (response.status === 401 && session) {
      reportUnauthorized(requestToken, requestSessionId);
    }
    throw error;
  }

  if (response.status === 204) return null;
  return response.json();
}
