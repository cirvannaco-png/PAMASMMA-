/**
 * PAMASMMA v4 — useAuth hook
 * Restores session from stored refresh token on mount.
 */
"use client";
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { loadStoredRefreshToken, auth, setTokens } from "@/lib/api";

export function useAuth() {
  const { isAuthenticated, userId, setAuth, clearAuth } = useAuthStore();
  const router = useRouter();
  const attempted = useRef(false);

  useEffect(() => {
    if (isAuthenticated || attempted.current) return;
    attempted.current = true;

    // Attempt silent refresh from stored refresh token
    loadStoredRefreshToken();
    // The api client will handle the refresh on the next authenticated call.
    // If it fails, it redirects to /auth automatically.
  }, [isAuthenticated]);

  const logout = async () => {
    try { await auth.logout(); } catch {}
    clearAuth();
    router.replace("/auth");
  };

  return { isAuthenticated, userId, logout };
}
