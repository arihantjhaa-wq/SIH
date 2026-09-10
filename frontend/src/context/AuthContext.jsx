import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import {
  registerUser,
  loginUser,
  developerAccessLogin,
  getCurrentUser,
  logoutUser,
} from "../services/authService.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const persistTokens = (accessToken) => {
    if (accessToken) {
      localStorage.setItem("ks_accessToken", accessToken);
    } else {
      localStorage.removeItem("ks_accessToken");
    }
  };

  const fetchCurrentUser = useCallback(async () => {
    const token = localStorage.getItem("ks_accessToken");
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const data = await getCurrentUser();
      setUser(data.user);
    } catch {
      persistTokens(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  const register = useCallback(async ({ username, email, password, name, address }) => {
    setError(null);
    setLoading(true);
    try {
      await registerUser({ username, email, password, name, address });
      const result = await loginUser({ username, password });
      persistTokens(result.accessToken);
      setUser(result.user);
      return result.user;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async ({ username, password }) => {
    setError(null);
    setLoading(true);
    try {
      const result = await loginUser({ username, password });
      persistTokens(result.accessToken);
      setUser(result.user);
      return result.user;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const developerLogin = useCallback(async ({ developerKey }) => {
    setError(null);
    setLoading(true);
    try {
      const result = await developerAccessLogin({ developerKey });
      persistTokens(result.accessToken);
      setUser(result.user);
      return result.user;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    // Clear local state immediately (synchronously) so isAuthenticated flips
    // false before the navigation handler runs. This prevents the back-button
    // race where the protected route could briefly re-render with stale state.
    persistTokens(null);
    setUser(null);

    // Best-effort server-side logout (don't await — clears cookies, revokes
    // refresh token; safe to fire-and-forget from the client's perspective).
    logoutUser().catch(() => {});
  }, []);

  const value = {
    user,
    isAuthenticated: !!user,
    loading,
    error,
    register,
    login,
    developerLogin,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
