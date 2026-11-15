import { AUTH_SESSION_KEY } from "../auth/session";

function decodeJwtPayload(token) {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    return JSON.parse(decodeURIComponent(escape(atob(padded))));
  } catch {
    return null;
  }
}

export function getSessionUser() {
  try {
    const session = JSON.parse(
      window.sessionStorage.getItem(AUTH_SESSION_KEY) || "null",
    );
    if (!session?.accessToken || !Number.isFinite(session.expiresAt)) return null;
    if (session.expiresAt <= Date.now()) return null;

    const payload = decodeJwtPayload(session.accessToken);
    if (!payload) return null;

    const id = Number(payload.sub);
    if (!Number.isSafeInteger(id) || id <= 0) return null;

    return {
      id,
      username: payload.username || session.username || "",
      role: payload.role || "employee",
    };
  } catch {
    return null;
  }
}

export function isOfflineError(error) {
  return !error?.status;
}