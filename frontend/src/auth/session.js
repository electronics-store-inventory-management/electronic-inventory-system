export const AUTH_SESSION_KEY = "electrostock.auth";

export function readStoredSession() {
  try {
    return JSON.parse(window.sessionStorage.getItem(AUTH_SESSION_KEY) || "null");
  } catch {
    return null;
  }
}

export function isSameSession(session, accessToken, sessionId) {
  return Boolean(accessToken && session?.accessToken === accessToken &&
    (session.sessionId ?? null) === (sessionId ?? null));
}

export function removeStoredSession(accessToken, sessionId) {
  if (isSameSession(readStoredSession(), accessToken, sessionId)) {
    window.sessionStorage.removeItem(AUTH_SESSION_KEY);
  }
}

export function clearAuthSession(setSession, accessToken, sessionId) {
  removeStoredSession(accessToken, sessionId);
  // Storage may already have been cleared by the API before its event was heard.
  setSession((current) => isSameSession(current, accessToken, sessionId) ? null : current);
}
