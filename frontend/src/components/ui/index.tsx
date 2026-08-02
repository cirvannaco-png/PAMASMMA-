/**
 * PAMASMMA v4 — UI Primitives
 * Button, Badge, Card — obsidian/gold/silver design system.
 */
import React from "react";

// ── Button ────────────────────────────────────────────────────────────────────
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  style,
  ...props
}: ButtonProps) {
  const base: React.CSSProperties = {
    border: "none",
    borderRadius: 12,
    fontWeight: 700,
    cursor: disabled || loading ? "not-allowed" : "pointer",
    opacity: disabled || loading ? 0.5 : 1,
    transition: "background 0.15s, transform 0.1s",
    fontFamily: "inherit",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  };

  const sizes: Record<string, React.CSSProperties> = {
    sm: { padding: "7px 14px", fontSize: 11 },
    md: { padding: "11px 20px", fontSize: 13 },
    lg: { padding: "14px 28px", fontSize: 14 },
  };

  const variants: Record<string, React.CSSProperties> = {
    primary: { background: "#6B3FFB", color: "#E8E8FA" },
    ghost:   { background: "transparent", color: "#8080D0", border: "1px solid #1E1E40" },
    danger:  { background: "#FF4D6D22", color: "#FF4D6D", border: "1px solid #FF4D6D40" },
  };

  return (
    <button
      disabled={disabled || loading}
      style={{ ...base, ...sizes[size], ...variants[variant], ...style }}
      {...props}
    >
      {loading ? <span style={{ opacity: 0.7 }}>…</span> : children}
    </button>
  );
}

// ── Badge ─────────────────────────────────────────────────────────────────────
interface BadgeProps {
  children: React.ReactNode;
  color?: string;
  style?: React.CSSProperties;
}

export function Badge({ children, color = "#6B3FFB", style }: BadgeProps) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "2px 8px", borderRadius: 6,
      fontSize: 9, fontWeight: 800, letterSpacing: 0.5,
      color: "#06060F", background: color,
      fontFamily: "monospace",
      ...style,
    }}>
      {children}
    </span>
  );
}

// ── Card ──────────────────────────────────────────────────────────────────────
interface CardProps {
  children: React.ReactNode;
  style?: React.CSSProperties;
  accent?: string;
}

export function Card({ children, style, accent }: CardProps) {
  return (
    <div style={{
      background: "#0C0C22",
      border: `1px solid ${accent ? `${accent}25` : "#161630"}`,
      borderRadius: 12,
      padding: "16px 20px",
      ...style,
    }}>
      {children}
    </div>
  );
}

// ── StatusDot ─────────────────────────────────────────────────────────────────
interface StatusDotProps {
  color?: string;
  pulse?: boolean;
}

export function StatusDot({ color = "#3BFFA0", pulse = true }: StatusDotProps) {
  return (
    <span style={{
      display: "inline-block",
      width: 6, height: 6,
      borderRadius: "50%",
      background: color,
      boxShadow: `0 0 6px ${color}80`,
      flexShrink: 0,
    }}
    className={pulse ? "animate-pulse-dot" : ""}
    />
  );
}

// ── Divider ───────────────────────────────────────────────────────────────────
export function Divider({ style }: { style?: React.CSSProperties }) {
  return (
    <div style={{ height: 1, background: "#161630", margin: "12px 0", ...style }} />
  );
}

// ── Label ─────────────────────────────────────────────────────────────────────
export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 8, letterSpacing: 2.5,
      color: "#3A3A6A", fontWeight: 700,
      marginBottom: 10, fontFamily: "monospace",
      textTransform: "uppercase",
    }}>
      {children}
    </div>
  );
}
