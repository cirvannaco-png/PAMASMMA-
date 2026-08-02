/**
 * PAMASMMA v4 — WebAuthn Prompt Component
 * Handles hardware key (YubiKey / Touch ID / Face ID) registration and auth.
 * Uses @simplewebauthn/browser under the hood.
 */
"use client";
import { useState } from "react";
import {
  startRegistration,
  startAuthentication,
} from "@simplewebauthn/browser";
import toast from "react-hot-toast";
import { auth } from "@/lib/api";
import { Button } from "@/components/ui";

interface WebAuthnRegisterProps {
  userId: string;
  username: string;
  onComplete: () => void;
}

interface WebAuthnAuthProps {
  userId: string;
  onComplete: () => void;
}

// ── Registration ──────────────────────────────────────────────────────────────
export function WebAuthnRegister({ userId, username, onComplete }: WebAuthnRegisterProps) {
  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    setLoading(true);
    try {
      // 1. Get challenge from server
      const options = await auth.webauthnRegisterBegin(userId, username);

      // 2. Browser prompts for hardware key / biometric
      const credential = await startRegistration(options as any);

      // 3. Verify with server
      await auth.webauthnRegisterComplete(userId, credential as any);

      toast.success("Hardware key registered ✓");
      onComplete();
    } catch (e: any) {
      if (e.name === "NotAllowedError") {
        toast.error("Registration cancelled or timed out");
      } else {
        toast.error(e.message ?? "WebAuthn registration failed");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <p style={{ fontSize: 11, color: "#6060A0", lineHeight: 1.6, marginBottom: 16 }}>
        Register a hardware security key (YubiKey), Touch ID, or Face ID as a
        second authentication factor. Requires a WebAuthn-compatible device.
      </p>
      <Button onClick={handleRegister} loading={loading} style={{ width: "100%" }}>
        Register Hardware Key →
      </Button>
    </div>
  );
}

// ── Authentication ────────────────────────────────────────────────────────────
export function WebAuthnAuth({ userId, onComplete }: WebAuthnAuthProps) {
  const [loading, setLoading] = useState(false);

  const handleAuth = async () => {
    setLoading(true);
    try {
      const options = await auth.webauthnAuthBegin(userId);
      const credential = await startAuthentication(options as any);
      await auth.webauthnAuthComplete(userId, credential as any);
      toast.success("WebAuthn authentication verified ✓");
      onComplete();
    } catch (e: any) {
      if (e.name === "NotAllowedError") {
        toast.error("Authentication cancelled or timed out");
      } else if ((e as any).status === 404) {
        toast.error("No hardware key registered for this account");
      } else {
        toast.error(e.message ?? "WebAuthn authentication failed");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <p style={{ fontSize: 11, color: "#6060A0", lineHeight: 1.6, marginBottom: 16 }}>
        Touch your hardware security key, or use Touch ID / Face ID to authenticate.
      </p>
      <Button onClick={handleAuth} loading={loading} style={{ width: "100%", background: "#D4AF37", color: "#06060F" }}>
        Authenticate with Key →
      </Button>
    </div>
  );
}
