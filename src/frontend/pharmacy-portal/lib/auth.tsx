"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<{ requiresMfa: boolean }>;
  verifyMfa: (code: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  loading: true,
  login: async () => ({ requiresMfa: false }),
  verifyMfa: async () => {},
  logout: () => {},
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedToken = localStorage.getItem("qes_token");
    const savedUser = localStorage.getItem("qes_user");
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Invalid credentials");
    }
    const data = await res.json();
    if (data.requires_mfa) {
      localStorage.setItem("qes_mfa_token", data.mfa_token);
      return { requiresMfa: true };
    }
    setToken(data.token);
    setUser(data.user);
    localStorage.setItem("qes_token", data.token);
    localStorage.setItem("qes_user", JSON.stringify(data.user));
    return { requiresMfa: false };
  }, []);

  const verifyMfa = useCallback(async (code: string) => {
    const mfaToken = localStorage.getItem("qes_mfa_token");
    const res = await fetch("/api/v1/auth/mfa/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mfa_token: mfaToken, code }),
    });
    if (!res.ok) throw new Error("Invalid verification code");
    const data = await res.json();
    localStorage.removeItem("qes_mfa_token");
    setToken(data.token);
    setUser(data.user);
    localStorage.setItem("qes_token", data.token);
    localStorage.setItem("qes_user", JSON.stringify(data.user));
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("qes_token");
    localStorage.removeItem("qes_user");
    localStorage.removeItem("qes_mfa_token");
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, verifyMfa, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
