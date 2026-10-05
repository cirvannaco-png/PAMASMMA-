/**
 * PAMASMMA v4.0.1 — Auth session hook
 * Restores a persisted refresh session before protected UI redirects fire.
 */
"use client";

import { useEffect, useRef } from "react";
import { decodeJwt } from "jose";
import { useRouter } from "next/navigation";

import { auth, restoreSession } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export function useAuth() {
  const { isAuthenticated, userId, setAuth, clearAuth } = useAuthStore();
  const router = useRouter();
  const attempted = useRef(false);

  useEffect(() => {
    if (isAuthenticated || attempted.current) return;
    attempted.current = true;

    void (async () => {
      const tokens = await restoreSession();
      if (!tokens) return;

      try {
        const payload = decodeJwt(tokens.access_token);
        const subject = typeof payload.sub === "string" ? payload.sub : null;

        if (!subject) {
          clearAuth();
          return;
        }

        setAuth(subject, tokens);
      } catch {
        clearAuth();
      }
    })();
  }, [clearAuth, isAuthenticated, setAuth]);

  const logout = async () => {
    try {
      await auth.logout();
    } catch {
      // Logout is best-effort; local credentials are still cleared.
    }
    clearAuth();
    router.replace("/auth");
  };

  return { isAuthenticated, userId, logout };
}
