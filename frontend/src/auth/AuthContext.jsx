import { createContext, useContext, useMemo, useState } from "react";
import { apiRequest, setAccessToken } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);

  async function login(username, password) {
    setLoading(true);
    try {
      const result = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
        authenticated: false,
      });
      setAccessToken(result.access_token);
      setUser(result.user);
      return result.user;
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    setAccessToken(null);
    setUser(null);
  }

  const value = useMemo(
    () => ({ user, loading, login, logout }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
