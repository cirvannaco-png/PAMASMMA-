"use client";
import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useCognitiveStore } from "@/lib/store";
import { SYSTEMS } from "@/lib/constants";
import type { SystemId } from "@/types";

/**
 * PAMASMMA v4 — Individual System Deep-Link Page
 * /dashboard/S1 → sets S1 active and redirects to /dashboard
 * Enables direct URL sharing for each cognitive system.
 */
export default function SystemPage() {
  const params = useParams();
  const router = useRouter();
  const { setActiveSystem } = useCognitiveStore();

  const systemParam = (params?.system as string)?.toUpperCase() as SystemId;
  const valid = SYSTEMS.some(s => s.id === systemParam);

  useEffect(() => {
    if (valid) {
      setActiveSystem(systemParam);
    }
    router.replace("/dashboard");
  }, [systemParam, valid]);

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "center",
      height: "100vh", background: "#04040D",
      color: "#3A3A6A", fontFamily: "monospace", fontSize: 12, letterSpacing: 2,
    }}>
      {valid
        ? `LOADING ${systemParam}…`
        : "UNKNOWN SYSTEM — REDIRECTING"}
    </div>
  );
}
