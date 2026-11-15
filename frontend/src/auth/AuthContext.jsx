import { useCallback, useEffect, useMemo, useState } from "react";
import { login as requestLogin } from "../services/authService";
import { AUTH_SESSION_KEY } from "./session";
import { AuthContext } from "./AuthContextValue";

const VALID_ROLES = new Set(["admin", "employee"]);

function readSession() {
  try {
    const session = JSON.parse(sessionStorage.getItem(AUTH_SESSION_KEY) || "null");
    if (
      !session?.accessToken ||
      !session.username ||
      !VALID_ROLES.has(session.role) ||
      !Number.isFinite(session.expiresAt) ||
      session.expiresAt <= Date.now()
    ) {
      sessionStorage.removeItem(AUTH_SESSION_KEY);
      return null;
    }
    return session;
  } catch {
    sessionStorage.removeItem(AUTH_SESSION_KEY);
    return null;
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readSession);

  const clearSessionIfCurrent = useCallback((accessToken, sessionId) => {
    if (!accessToken) return;

    let storedSession = null;
    try {
      storedSession = JSON.parse(
        sessionStorage.getItem(AUTH_SESSION_KEY) || "null",
      );
    } catch {
      // Treat malformed stored state as absent.
    }

    if (
      storedSession?.accessToken !== accessToken ||
      (storedSession?.sessionId || null) !== sessionId
    ) {
      return;
    }

    sessionStorage.removeItem(AUTH_SESSION_KEY);
    setSession((current) =>
      current?.accessToken === accessToken &&
      (current?.sessionId || null) === sessionId
        ? null
        : current,
    );
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(AUTH_SESSION_KEY);
    setSession(null);
  }, []);

  const signIn = useCallback(async (username, password) => {
    const result = await requestLogin(username, password);
    const nextSession = {
      accessToken: result.accessToken,
      sessionId: crypto.randomUUID(),
      tokenType: result.tokenType,
      username,
      role: result.role,
      expiresAt: Date.now() + result.expiresIn * 1000,
    };
    sessionStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(nextSession));
    setSession(nextSession);
  }, []);

  useEffect(() => {
    const handleUnauthorized = (event) => {
      const accessToken = event.detail?.accessToken;
      const sessionId = event.detail?.sessionId;
      if (!accessToken) return;
      setSession((current) =>
        current?.accessToken === accessToken &&
        (current?.sessionId || null) === sessionId
          ? null
          : current,
      );
    };
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, [clearSessionIfCurrent]);

  useEffect(() => {
    if (!session) return undefined;
    const checkExpiry = () => {
      if (session.expiresAt <= Date.now()) {
        clearSessionIfCurrent(session.accessToken, session.sessionId);
      }
    };
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") checkExpiry();
    };
    const timer = window.setTimeout(
      checkExpiry,
      Math.max(0, session.expiresAt - Date.now()),
    );
    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("focus", checkExpiry);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("focus", checkExpiry);
    };
  }, [session, clearSessionIfCurrent]);

  const value = useMemo(
    () => ({
      session,
      user: session
        ? { username: session.username, role: session.role }
        : null,
      isAuthenticated: Boolean(session),
      signIn,
      logout,
    }),
    [session, signIn, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
