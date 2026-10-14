"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { getMe, updateProfile, type User, type UserProfile } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  /** Update profile fields and refresh user state */
  updateUserProfile: (data: Partial<UserProfile>) => Promise<void>;
  /** Clear token and reset state */
  logout: () => void;
  /** True if user has non-default profile values */
  hasCustomProfile: boolean;
  /** Save token and set authenticated user */
  login: (token: string) => Promise<void>;
}

// ── Context ───────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("erudios_token")
        : null;

    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const me = await getMe();
      setUser(me);
    } catch {
      // Token invalid or expired — clear it
      localStorage.removeItem("erudios_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchUser();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchUser]);

  const login = useCallback(async (token: string) => {
    localStorage.setItem("erudios_token", token);
    setLoading(true);
    try {
      const me = await getMe();
      setUser(me);
    } catch (err) {
      localStorage.removeItem("erudios_token");
      setUser(null);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateUserProfile = useCallback(
    async (data: Partial<UserProfile>) => {
      const updated = await updateProfile(data);
      setUser(updated);
    },
    []
  );

  const logout = useCallback(() => {
    localStorage.removeItem("erudios_token");
    setUser(null);
  }, []);

  const hasCustomProfile =
    !!user &&
    (user.level !== "beginner" ||
      user.learning_style !== "practical" ||
      user.goal !== "general");

  return (
    <AuthContext.Provider
      value={{ user, loading, updateUserProfile, logout, hasCustomProfile, login }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
