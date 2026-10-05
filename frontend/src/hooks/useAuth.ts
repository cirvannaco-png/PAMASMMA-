/**
 * PAMASMMA — Auth session hook.
 * Restores the refresh session before protected UI decides whether to redirect.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { decodeJwt } from "jose";
import { useRouter } from "next/navigation";

import { auth, restoreSession } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export function useAuth() {
  const { isAuthenticated, userId, setAuth, clearAuth } = useAuthStore();
  const router = useRouter();
  const attempted = useRef(false);
  const [isRestoring, setIsRestoring] = useState(!isAuthenticated);

  useEffect(() => {
    if (isAuthenticated || attempted.current) {
      setIsRestoring(false);
      return;
    }

    attempted.current = true;
    let cancelled = false;

    void (async () => {
      try {
        const tokens = await restoreSession();
        if (!tokens) return;

        const payload = decodeJwt(tokens.access_token);
        const subject = typeof payload.sub === "string" ? payload.sub : null;

        if (!subject) {
          clearAuth();
          return;
        }

        if (!cancelled) {
          setAuth(subject, tokens);
        }
      } catch {
        if (!cancelled) {
          clearAuth();
        }
      } finally {
        if (!cancelled) {
          setIsRestoring(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
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

  return { isAuthenticated, userId, isRestoring, logout };
}
