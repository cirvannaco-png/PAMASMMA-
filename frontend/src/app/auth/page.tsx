"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import QRCode from "qrcode";
import { startAuthentication } from "@simplewebauthn/browser";
import toast from "react-hot-toast";

import { auth } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

type AuthMode = "loading" | "setup" | "signin";
type SignInMethod = "totp" | "webauthn";

const FOUNDER_ID = process.env.NEXT_PUBLIC_FOUNDER_USER_ID ?? "kelson-mwangi-cirvanna";
const FOUNDER_USERNAME = process.env.NEXT_PUBLIC_FOUNDER_USERNAME ?? "kelson@cirvanna.co";

export default function AuthPage() {
  const router = useRouter();
  const { isAuthenticated, setAuth } = useAuthStore();

  const [mode, setMode] = useState<AuthMode>("loading");
  const [method, setMethod] = useState<SignInMethod>("totp");
  const [bootstrapToken, setBootstrapToken] = useState("");
  const [secret, setSecret] = useState("");
  const [qrDataUrl, setQrDataUrl] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({
    setup_required: false,
    totp_enabled: false,
    webauthn_registered: false,
  });

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/dashboard");
      return;
    }

    void auth.status(FOUNDER_ID)
      .then((data) => {
        setStatus(data);
        setMode(data.setup_required ? "setup" : "signin");
        if (!data.totp_enabled && data.webauthn_registered) {
          setMethod("webauthn");
        }
      })
      .catch((error) => {
        toast.error(error instanceof Error ? error.message : "Unable to reach PAMASMMA");
        setMode("signin");
      });
  }, [isAuthenticated, router]);

  const loginMethods = useMemo(
    () => [
      { id: "totp" as const, label: "Authenticator", enabled: status.totp_enabled || Boolean(secret) },
      { id: "webauthn" as const, label: "Passkey / Security Key", enabled: status.webauthn_registered },
    ],
    [status, secret],
  );

  const completeLogin = (tokens: Awaited<ReturnType<typeof auth.totpVerify>>) => {
    setAuth(FOUNDER_ID, tokens);
    toast.success("PAMASMMA access granted");
    router.replace("/dashboard");
  };

  const handleSetup = async () => {
    if (!bootstrapToken.trim()) {
      toast.error("Enter the bootstrap enrollment token.");
      return;
    }

    setLoading(true);
    try {
      const data = await auth.totpSetup(FOUNDER_ID, FOUNDER_USERNAME, bootstrapToken.trim());
      setSecret(data.secret);
      setQrDataUrl(await QRCode.toDataURL(data.uri, {
        width: 220,
        margin: 2,
        color: { dark: "#E8E8FA", light: "#07071A" },
      }));
      setMode("signin");
      setStatus((current) => ({
        ...current,
        setup_required: false,
        totp_enabled: false,
        webauthn_registered: false,
      }));
      toast.success("Authenticator secret created. Scan it, then sign in.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Enrollment failed");
    } finally {
      setLoading(false);
    }
  };

  const handleTotpLogin = async () => {
    if (code.length !== 6) return;
    setLoading(true);
    try {
      completeLogin(await auth.totpVerify(FOUNDER_ID, code));
    } catch (error) {
      setCode("");
      toast.error(error instanceof Error ? error.message : "Invalid authenticator code");
    } finally {
      setLoading(false);
    }
  };

  const handleWebAuthnLogin = async () => {
    setLoading(true);
    try {
      const options = await auth.webauthnAuthBegin(FOUNDER_ID);
      const credential = await startAuthentication(options as any);
      completeLogin(await auth.webauthnAuthComplete(FOUNDER_ID, credential as any));
    } catch (error: any) {
      if (error?.name === "NotAllowedError") {
        toast.error("Authentication was cancelled or timed out.");
      } else {
        toast.error(error instanceof Error ? error.message : "Passkey authentication failed");
      }
    } finally {
      setLoading(false);
    }
  };

  if (mode === "loading") {
    return (
      <main className="grid min-h-screen place-items-center bg-[#04040D] px-6 text-[#6D6DA0]">
        <div className="text-center font-mono text-xs tracking-[0.24em]">
          INITIALIZING SECURE ACCESS…
        </div>
      </main>
    );
  }

  if (mode === "setup") {
    return (
      <main className="min-h-screen bg-[#04040D] px-6 py-10 text-[#D0D0EC]">
        <div className="mx-auto flex min-h-[80vh] max-w-md items-center">
          <div className="w-full">
            <Link href="/" className="font-mono text-[9px] tracking-[0.24em] text-[#51517A] hover:text-[#8585AD]">
              ← PAMASMMA
            </Link>
            <div className="mt-8 rounded-3xl border border-[#222243] bg-[#07071A] p-7 shadow-[0_30px_90px_rgba(0,0,0,.35)]">
              <div className="font-mono text-[9px] tracking-[0.24em] text-[#6B3FFB]">FIRST-TIME ENROLLMENT</div>
              <h1 className="mt-3 text-2xl font-semibold text-[#EDEDF7]">Establish founder access.</h1>
              <p className="mt-3 text-sm leading-7 text-[#66668B]">
                PAMASMMA generates the authenticator secret once and stores only an encrypted copy on the server.
              </p>
              <div className="mt-6 rounded-2xl border border-[#191936] bg-[#0A0A20] p-4">
                <div className="font-mono text-[9px] tracking-[0.18em] text-[#4E4E75]">IDENTITY</div>
                <div className="mt-2 text-sm text-[#B9B9D0]">{FOUNDER_USERNAME}</div>
              </div>
              <input
                type="password"
                value={bootstrapToken}
                onChange={(event) => setBootstrapToken(event.target.value)}
                placeholder="Bootstrap enrollment token"
                autoComplete="off"
                className="mt-5 w-full rounded-2xl border border-[#25254A] bg-[#0A0A20] px-4 py-3 text-sm text-[#E6E6F5] outline-none placeholder:text-[#44446C] focus:border-[#6B3FFB]"
              />
              <button
                onClick={handleSetup}
                disabled={loading}
                className="mt-3 w-full rounded-2xl bg-[#6B3FFB] px-4 py-3.5 text-sm font-bold text-white transition hover:bg-[#7951FF] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "Creating secure enrollment…" : "Create authenticator →"}
              </button>
              <p className="mt-4 text-center text-[10px] leading-5 text-[#414166]">
                The bootstrap token is never stored in browser storage.
              </p>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#04040D] px-6 py-10 text-[#D0D0EC]">
      <div className="mx-auto flex min-h-[80vh] max-w-5xl items-center">
        <div className="grid w-full gap-8 lg:grid-cols-[1fr_420px] lg:items-center">
          <div className="hidden lg:block">
            <Link href="/" className="font-mono text-[9px] tracking-[0.24em] text-[#51517A] hover:text-[#8585AD]">← PAMASMMA</Link>
            <div className="mt-10 max-w-2xl">
              <div className="font-mono text-[9px] tracking-[0.24em] text-[#6B3FFB]">SECURE FOUNDER ACCESS</div>
              <h1 className="mt-4 text-5xl font-semibold leading-tight tracking-tight text-[#F0F0F8]">
                The console is private.
                <span className="block text-[#8D77FF]">The thinking is governed.</span>
              </h1>
              <p className="mt-5 max-w-xl text-sm leading-7 text-[#67678C]">
                Authenticate to enter the ten-system cognitive console, inspect action history,
                invoke intelligence, and manage governed overrides.
              </p>
            </div>
          </div>

          <div className="rounded-3xl border border-[#222243] bg-[#07071A] p-7 shadow-[0_30px_90px_rgba(0,0,0,.35)] sm:p-8">
            <Link href="/" className="font-mono text-[9px] tracking-[0.24em] text-[#51517A] lg:hidden">← PAMASMMA</Link>
            <div className="mt-7 lg:mt-0">
              <div className="font-mono text-[9px] tracking-[0.24em] text-[#6B3FFB]">AUTHENTICATE</div>
              <h2 className="mt-2 text-2xl font-semibold text-[#EDEDF7]">Welcome back.</h2>
              <p className="mt-2 text-xs leading-6 text-[#626286]">{FOUNDER_USERNAME}</p>
            </div>

            {secret && qrDataUrl && (
              <div className="mt-6 rounded-2xl border border-[#2B2850] bg-[#0A0A20] p-4">
                <div className="font-mono text-[9px] tracking-[0.16em] text-[#676796]">SCAN TO COMPLETE ENROLLMENT</div>
                <div className="mt-4 flex justify-center">
                  <Image src={qrDataUrl} alt="TOTP enrollment QR code" width={190} height={190} unoptimized />
                </div>
                <div className="mt-4 break-all rounded-xl border border-[#1A1A35] bg-[#07071A] p-3 text-center font-mono text-[10px] text-[#686890]">
                  {secret}
                </div>
              </div>
            )}

            <div className="mt-6 grid grid-cols-2 gap-2">
              {loginMethods.map((item) => (
                <button
                  key={item.id}
                  onClick={() => item.enabled && setMethod(item.id)}
                  disabled={!item.enabled}
                  className={
                    "rounded-xl border px-3 py-2.5 text-left transition " +
                    (method === item.id
                      ? "border-[#6B3FFB80] bg-[#6B3FFB14] text-[#E5E5F3]"
                      : "border-[#191936] bg-[#09091D] text-[#626286]") +
                    (!item.enabled ? " cursor-not-allowed opacity-40" : " hover:border-[#3A3A62]")
                  }
                >
                  <div className="text-[11px] font-semibold">{item.label}</div>
                  <div className="mt-1 text-[9px] text-[#49496D]">{item.id === "totp" && secret && !status.totp_enabled ? "Ready to verify" : item.enabled ? "Available" : "Not configured"}</div>
                </button>
              ))}
            </div>

            {method === "totp" && status.totp_enabled && (
              <div className="mt-5">
                <input
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={code}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                  onKeyDown={(event) => { if (event.key === "Enter") void handleTotpLogin(); }}
                  placeholder="000000"
                  maxLength={6}
                  className="w-full rounded-2xl border border-[#25254A] bg-[#0A0A20] px-4 py-4 text-center font-mono text-3xl font-bold tracking-[.5em] text-[#E8E8FA] outline-none placeholder:text-[#343455] focus:border-[#6B3FFB]"
                />
                <button
                  onClick={() => void handleTotpLogin()}
                  disabled={loading || code.length !== 6}
                  className="mt-3 w-full rounded-2xl bg-[#6B3FFB] px-4 py-3.5 text-sm font-bold text-white transition hover:bg-[#7951FF] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {loading ? "Verifying…" : "Enter console →"}
                </button>
              </div>
            )}

            {method === "webauthn" && status.webauthn_registered && (
              <div className="mt-5">
                <button
                  onClick={() => void handleWebAuthnLogin()}
                  disabled={loading}
                  className="w-full rounded-2xl bg-[#D4AF37] px-4 py-3.5 text-sm font-bold text-[#07070F] transition hover:bg-[#E5C55A] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loading ? "Waiting for credential…" : "Use passkey / security key →"}
                </button>
              </div>
            )}

            {!status.totp_enabled && !status.webauthn_registered && !secret && (
              <div className="mt-5 rounded-2xl border border-[#D4AF3730] bg-[#D4AF3708] p-4 text-xs leading-6 text-[#8F835B]">
                Enrollment is incomplete. Refresh this page after finishing authenticator setup.
              </div>
            )}

            <div className="mt-6 border-t border-[#17172F] pt-5 text-center">
              <Link href="/" className="text-[10px] text-[#4C4C72] transition hover:text-[#76769D]">Return to public gateway</Link>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
