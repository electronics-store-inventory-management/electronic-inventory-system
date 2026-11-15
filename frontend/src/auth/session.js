export const AUTH_SESSION_KEY = "electrostock.auth";

// The token claim drives display only. The API authorizes each request.
export function getSessionRole(accessToken) {
  try {
    const payload = accessToken.split(".")[1];
    const { role } = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return role === "admin" || role === "employee" ? role : null;
  } catch {
    return null;
  }
}
