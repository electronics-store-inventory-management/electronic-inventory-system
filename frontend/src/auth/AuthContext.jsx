import { useCallback, useEffect, useMemo, useState } from "react";
import { getAccount, login as requestLogin } from "../services/authService";
import { AUTH_SESSION_KEY, clearAuthSession } from "./session";
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
  const [sessionError, setSessionError] = useState("");
  const [sessionAttempt, setSessionAttempt] = useState(0);

  const clearSessionIfCurrent = useCallback((accessToken, sessionId) => {
    clearAuthSession(setSession, accessToken, sessionId);
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(AUTH_SESSION_KEY);
    setSession(null);
    setSessionError("");
  }, []);

  const retrySession = useCallback(() => {
    setSessionError("");
    setSessionAttempt((attempt) => attempt + 1);
  }, []);

  const signIn = useCallback(async (username, password) => {
    const result = await requestLogin(username, password);
    const expiresAt = Date.now() + result.expiresIn * 1000;
    const user = await getAccount({ accessToken: result.accessToken });
    if (expiresAt <= Date.now()) throw new Error("Your session has expired. Sign in again.");
    const nextSession = {
      accessToken: result.accessToken,
      sessionId: crypto.randomUUID(),
      tokenType: result.tokenType,
      username: user.username,
      role: user.role,
      expiresAt,
    };
    sessionStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(nextSession));
    setSessionError("");
    setSession({ ...nextSession, user });
  }, []);

  useEffect(() => {
    const handleUnauthorized = (event) => {
      clearSessionIfCurrent(event.detail?.accessToken, event.detail?.sessionId);
    };
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, [clearSessionIfCurrent]);

  useEffect(() => {
    if (!session || session.user) return undefined;

    const controller = new AbortController();
    getAccount({ signal: controller.signal }).then((user) => {
      if (controller.signal.aborted) return;
      if (session.expiresAt <= Date.now()) {
        clearSessionIfCurrent(session.accessToken, session.sessionId);
        return;
      }
      setSession((current) => current === session ? { ...current, user } : current);
    }).catch((error) => {
      if (controller.signal.aborted) return;
      if (error.status === 401 || session.expiresAt <= Date.now()) {
        clearSessionIfCurrent(session.accessToken, session.sessionId || null);
        return;
      }
      setSessionError("Could not verify your session. Check your connection and retry.");
    });
    return () => controller.abort();
  }, [session, sessionAttempt, clearSessionIfCurrent]);

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
      user: session?.user ?? null,
      isAuthenticated: Boolean(session?.user),
      sessionError,
      retrySession,
      signIn,
      logout,
    }),
    [session, signIn, logout, sessionError, retrySession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
