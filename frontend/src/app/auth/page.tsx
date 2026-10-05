"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import QRCode from "qrcode";
import toast from "react-hot-toast";
import { auth } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

type Step = "setup" | "qr" | "verify";

const FOUNDER_ID = process.env.NEXT_PUBLIC_FOUNDER_USER_ID ?? "kelson-mwangi-cirvanna";
const FOUNDER_USERNAME = process.env.NEXT_PUBLIC_FOUNDER_USERNAME ?? "kelson@cirvanna.co";

const BOOT_LINES = [
  "PAMASMMA v4.0.1 — GOVERNED SYNTHETIC EXECUTIVE INTELLIGENCE",
  "Auth layer: TOTP + WebAuthn/FIDO2",
  "Identity principal: Kelson Mwangi @ Cirvanna",
  "Awaiting authentication…",
];

export default function AuthPage() {
  const router = useRouter();
  const { isAuthenticated, setAuth } = useAuthStore();

  const [step, setStep] = useState<Step>("setup");
  const [totpSecret, setTotpSecret] = useState("");
  const [bootstrapToken, setBootstrapToken] = useState("");
  const [totpUri, setTotpUri] = useState("");
  const [qrDataUrl, setQrDataUrl] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [bootDone, setBootDone] = useState(false);
  const [bootStep, setBootStep] = useState(0);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) router.replace("/dashboard");
  }, [isAuthenticated]);

  // Boot animation
  useEffect(() => {
    if (bootStep >= BOOT_LINES.length) {
      setTimeout(() => setBootDone(true), 400);
      return;
    }
    const t = setTimeout(() => setBootStep(s => s + 1), 350);
    return () => clearTimeout(t);
  }, [bootStep]);

  const handleSetupTOTP = async () => {
    if (!bootstrapToken.trim()) {
      toast.error("Enter the bootstrap enrollment token.");
      return;
    }

    setLoading(true);
    try {
      const res = await auth.totpSetup(FOUNDER_ID, FOUNDER_USERNAME, bootstrapToken.trim());
      setTotpSecret(res.secret);
      setTotpUri(res.uri);
      const dataUrl = await QRCode.toDataURL(res.uri, {
        width: 200,
        margin: 2,
        color: { dark: "#E8E8FA", light: "#07071A" },
      });
      setQrDataUrl(dataUrl);
      setStep("qr");
    } catch (e: any) {
      toast.error(e.message ?? "TOTP setup failed");
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    if (code.length < 6) return;
    setLoading(true);
    try {
      const tokens = await auth.totpVerify(FOUNDER_ID, code);
      setAuth(FOUNDER_ID, tokens);
      toast.success("Authentication successful");
      router.replace("/dashboard");
    } catch (e: any) {
      toast.error(e.message ?? "Invalid code — try again");
      setCode("");
    } finally {
      setLoading(false);
    }
  };

  const inputBoxStyle = (active: boolean): React.CSSProperties => ({
    background: "#0C0C22",
    border: `1px solid ${active ? "#6B3FFB" : "#1E1E40"}`,
    borderRadius: 12,
    padding: "14px 18px",
    color: "#DDE0F0",
    fontSize: 13,
    fontFamily: "inherit",
    outline: "none",
    width: "100%",
    transition: "border-color 0.15s",
  });

  // ── Boot screen ──────────────────────────────────────────────────────────
  if (!bootDone) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "#04040D", fontFamily: "'JetBrains Mono', monospace" }}>
        <div style={{ maxWidth: 520, width: "100%", padding: "0 24px" }}>
          <div style={{ fontSize: 26, fontWeight: 800, color: "#6B3FFB", letterSpacing: 5, marginBottom: 6, display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: 34 }}>⬡</span> PAMASMMA
          </div>
          <div style={{ fontSize: 10, color: "#3A3A6A", letterSpacing: 2, marginBottom: 32 }}>Governed Synthetic Executive Intelligence</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 9, marginBottom: 28 }}>
            {BOOT_LINES.slice(0, bootStep).map((line, i) => (
              <div key={i} style={{ fontSize: 11.5, color: i === bootStep - 1 ? "#00D4FF" : "#2A2A5A", display: "flex", gap: 8 }}>
                <span>{i < bootStep - 1 ? "✓" : "▶"}</span> {line}
              </div>
            ))}
            {bootStep < BOOT_LINES.length && (
              <span style={{ color: "#6B3FFB", fontSize: 14, animation: "blink 0.9s step-end infinite" }}>▮</span>
            )}
          </div>
          <div style={{ height: 2, background: "#161630", borderRadius: 2, overflow: "hidden" }}>
            <div style={{ height: "100%", background: "linear-gradient(90deg,#6B3FFB,#00D4FF)", width: `${(bootStep / BOOT_LINES.length) * 100}%`, transition: "width 0.35s" }} />
          </div>
        </div>
      </div>
    );
  }

  // ── Auth UI ───────────────────────────────────────────────────────────────
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "#04040D" }}>
      <div style={{ maxWidth: 420, width: "100%", padding: "0 24px" }}>

        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{ fontSize: 36, color: "#6B3FFB", marginBottom: 8 }}>⬡</div>
          <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: 4, color: "#E8E8FA" }}>PAMASMMA</div>
          <div style={{ fontSize: 9, color: "#3A3A6A", letterSpacing: 2, marginTop: 4 }}>SYNTHETIC EXECUTIVE INTELLIGENCE</div>
        </div>

        {/* Card */}
        <div style={{ background: "#07071A", border: "1px solid #161630", borderRadius: 16, padding: 28 }}>

          {/* ── Step: Setup ── */}
          {step === "setup" && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#E8E8FA", marginBottom: 6 }}>Authenticate as Founder</div>
              <div style={{ fontSize: 11, color: "#3A3A6A", marginBottom: 24, lineHeight: 1.6 }}>
                PAMASMMA uses TOTP (Time-based One-Time Password) as its primary auth layer. Set up once on your authenticator app.
              </div>
              <div style={{ background: "#0C0C22", border: "1px solid #161630", borderRadius: 10, padding: "12px 16px", marginBottom: 20 }}>
                <div style={{ fontSize: 9, color: "#3A3A6A", letterSpacing: 1.5, marginBottom: 6, fontFamily: "monospace" }}>IDENTITY PRINCIPAL</div>
                <div style={{ fontSize: 12, color: "#A0A0C0" }}>{FOUNDER_USERNAME}</div>
              </div>
              <input
                type="password"
                value={bootstrapToken}
                onChange={e => setBootstrapToken(e.target.value)}
                placeholder="Bootstrap enrollment token"
                autoComplete="off"
                style={{ ...inputBoxStyle(bootstrapToken.length > 0), marginBottom: 12 }}
              />
              <div style={{ fontSize: 9, color: "#2A2A5A", marginBottom: 16, lineHeight: 1.5 }}>
                This token is used only for first-time enrollment and is never stored by the browser.
              </div>
              <button
                onClick={handleSetupTOTP}
                disabled={loading}
                style={{ width: "100%", padding: "13px 0", borderRadius: 12, border: "none", background: "#6B3FFB", color: "#E8E8FA", fontSize: 13, fontWeight: 700, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.6 : 1, letterSpacing: 1 }}
              >
                {loading ? "Generating…" : "Generate TOTP Secret →"}
              </button>
            </div>
          )}

          {/* ── Step: QR ── */}
          {step === "qr" && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#E8E8FA", marginBottom: 6 }}>Scan with Authenticator</div>
              <div style={{ fontSize: 11, color: "#3A3A6A", marginBottom: 20, lineHeight: 1.6 }}>
                Scan the QR code with Google Authenticator, Authy, or 1Password. Then enter the 6-digit code below.
              </div>
              {qrDataUrl && (
                <div style={{ display: "flex", justifyContent: "center", marginBottom: 20 }}>
                  <div style={{ padding: 12, background: "#07071A", border: "1px solid #6B3FFB30", borderRadius: 12 }}>
                    <img src={qrDataUrl} alt="TOTP QR Code" width={180} height={180} />
                  </div>
                </div>
              )}
              <div style={{ background: "#0C0C22", border: "1px solid #161630", borderRadius: 10, padding: "10px 14px", marginBottom: 20, fontFamily: "monospace", fontSize: 11, color: "#6060A0", wordBreak: "break-all", lineHeight: 1.5 }}>
                {totpSecret}
              </div>
              <button
                onClick={() => setStep("verify")}
                style={{ width: "100%", padding: "13px 0", borderRadius: 12, border: "none", background: "#6B3FFB", color: "#E8E8FA", fontSize: 13, fontWeight: 700, cursor: "pointer", letterSpacing: 1 }}
              >
                I've scanned it — Enter Code →
              </button>
            </div>
          )}

          {/* ── Step: Verify ── */}
          {step === "verify" && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#E8E8FA", marginBottom: 6 }}>Enter TOTP Code</div>
              <div style={{ fontSize: 11, color: "#3A3A6A", marginBottom: 20, lineHeight: 1.6 }}>
                Enter the 6-digit code from your authenticator app.
              </div>
              <input
                type="text"
                value={code}
                onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                onKeyDown={e => { if (e.key === "Enter") handleVerify(); }}
                placeholder="000000"
                maxLength={6}
                style={{
                  ...inputBoxStyle(code.length > 0),
                  textAlign: "center",
                  fontSize: 28,
                  fontWeight: 800,
                  letterSpacing: 12,
                  fontFamily: "monospace",
                  marginBottom: 16,
                }}
                autoFocus
              />
              <button
                onClick={handleVerify}
                disabled={loading || code.length < 6}
                style={{ width: "100%", padding: "13px 0", borderRadius: 12, border: "none", background: code.length === 6 && !loading ? "#6B3FFB" : "#1A1A3A", color: "#E8E8FA", fontSize: 13, fontWeight: 700, cursor: code.length === 6 && !loading ? "pointer" : "not-allowed", letterSpacing: 1, opacity: code.length < 6 ? 0.5 : 1 }}
              >
                {loading ? "Verifying…" : "Authenticate →"}
              </button>
              <button onClick={() => { setCode(""); setStep("qr"); }} style={{ width: "100%", marginTop: 10, padding: "10px 0", borderRadius: 12, border: "1px solid #1E1E40", background: "none", color: "#3A3A6A", fontSize: 11, cursor: "pointer" }}>
                ← Back to QR code
              </button>
            </div>
          )}
        </div>

        <div style={{ textAlign: "center", marginTop: 20, fontSize: 9, color: "#1A1A3A", letterSpacing: 2, fontFamily: "monospace" }}>
          PAMASMMA v4.0.1 · MALI v7 · CIRVANNA
        </div>
      </div>
    </div>
  );
}
