/**
 * PAMASMMA v4 — TOTPSetup Component
 * Reusable TOTP setup flow: generate secret → display QR → verify code.
 * Used on /auth page and in settings.
 */
"use client";
import Image from "next/image";
import { useState } from "react";
import QRCode from "qrcode";
import toast from "react-hot-toast";
import { auth } from "@/lib/api";
import { Button } from "@/components/ui";

interface TOTPSetupProps {
  userId: string;
  username: string;
  bootstrapToken: string;
  onComplete: (secret: string) => void;
}

type Step = "generate" | "scan" | "verify";

export function TOTPSetup({ userId, username, bootstrapToken, onComplete }: TOTPSetupProps) {
  const [step, setStep]           = useState<Step>("generate");
  const [secret, setSecret]       = useState("");
  const [uri, setUri]             = useState("");
  const [qrDataUrl, setQrDataUrl] = useState("");
  const [code, setCode]           = useState("");
  const [loading, setLoading]     = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const res = await auth.totpSetup(userId, username, bootstrapToken);
      setSecret(res.secret);
      setUri(res.uri);
      const dataUrl = await QRCode.toDataURL(res.uri, {
        width: 200,
        margin: 2,
        color: { dark: "#E8E8FA", light: "#07071A" },
      });
      setQrDataUrl(dataUrl);
      setStep("scan");
    } catch (e: any) {
      toast.error(e.message ?? "Failed to generate TOTP secret");
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    if (code.length < 6) return;
    setLoading(true);
    try {
      await auth.totpVerify(userId, code);
      toast.success("TOTP verified — authenticator configured");
      onComplete(secret);
    } catch (e: any) {
      toast.error(e.message ?? "Invalid code");
      setCode("");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    background: "#0C0C22",
    border: "1px solid #1E1E40",
    borderRadius: 10,
    padding: "12px 16px",
    color: "#DDE0F0",
    fontSize: 13,
    fontFamily: "inherit",
    outline: "none",
    width: "100%",
  };

  return (
    <div>
      {step === "generate" && (
        <div>
          <p style={{ fontSize: 11, color: "#6060A0", lineHeight: 1.6, marginBottom: 16 }}>
            PAMASMMA uses TOTP as its primary auth layer. You’ll need Google
            Authenticator, Authy, or 1Password to scan the QR code.
          </p>
          <Button onClick={handleGenerate} loading={loading} style={{ width: "100%" }}>
            Generate TOTP Secret →
          </Button>
        </div>
      )}

      {step === "scan" && (
        <div>
          <p style={{ fontSize: 11, color: "#6060A0", lineHeight: 1.6, marginBottom: 16 }}>
            Scan with your authenticator app, then enter the 6-digit code below.
          </p>
          {qrDataUrl && (
            <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
              <div style={{ padding: 12, background: "#07071A", border: "1px solid #6B3FFB30", borderRadius: 12 }}>
                <Image src={qrDataUrl} alt="TOTP QR Code" width={180} height={180} unoptimized />
              </div>
            </div>
          )}
          <div style={{ background: "#0C0C22", borderRadius: 8, padding: "8px 12px", marginBottom: 16, fontFamily: "monospace", fontSize: 10, color: "#4040A0", wordBreak: "break-all", lineHeight: 1.6 }}>
            {secret}
          </div>
          <Button onClick={() => setStep("verify")} style={{ width: "100%" }}>
            I’ve scanned it →
          </Button>
        </div>
      )}

      {step === "verify" && (
        <div>
          <p style={{ fontSize: 11, color: "#6060A0", lineHeight: 1.6, marginBottom: 16 }}>
            Enter the 6-digit code from your authenticator app.
          </p>
          <input
            type="text"
            value={code}
            onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            onKeyDown={e => { if (e.key === "Enter") handleVerify(); }}
            placeholder="000000"
            maxLength={6}
            autoFocus
            style={{
              ...inputStyle,
              textAlign: "center",
              fontSize: 28,
              fontWeight: 800,
              letterSpacing: 14,
              fontFamily: "monospace",
              marginBottom: 12,
            }}
          />
          <Button
            onClick={handleVerify}
            loading={loading}
            disabled={code.length < 6}
            style={{ width: "100%" }}
          >
            Verify Code →
          </Button>
          <button
            onClick={() => { setStep("scan"); setCode(""); }}
            style={{ width: "100%", marginTop: 8, padding: "9px 0", background: "none", border: "1px solid #1E1E40", borderRadius: 10, color: "#3A3A6A", fontSize: 11, cursor: "pointer" }}
          >
            ← Back to QR code
          </button>
        </div>
      )}
    </div>
  );
}
