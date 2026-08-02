/**
 * PAMASMMA v4 — Frontend Constants
 * Single source of truth for system metadata and personality baseline.
 */
import type { CognitiveSystem } from "@/types";

export const SYSTEMS: CognitiveSystem[] = [
  { id: "S1",  name: "Executive Operations",    color: "#6B3FFB" },
  { id: "S2",  name: "Marketing Intelligence",  color: "#00D4FF" },
  { id: "S3",  name: "Relationship Management", color: "#D4AF37" },
  { id: "S4",  name: "Creator Economy",         color: "#3BFFA0" },
  { id: "S5",  name: "Narrative Governance",    color: "#FF5B8B" },
  { id: "S6",  name: "Audience Psychology",     color: "#FF8C42" },
  { id: "S7",  name: "Behavioral Consistency",  color: "#A97FFF" },
  { id: "S8",  name: "Persuasion Governance",   color: "#FF4D6D" },
  { id: "S9",  name: "Voice & Presence",        color: "#5BFFD0" },
  { id: "S10", name: "Strategic Narrative",     color: "#FFD700" },
];

export const PERSONALITY = [
  { key: "ASS", label: "Assertiveness",    val: 0.84 },
  { key: "VBY", label: "Verbosity",        val: 0.72 },
  { key: "FML", label: "Formality",        val: 0.61 },
  { key: "SDT", label: "Strategic Depth",  val: 0.91 },
];

export const SYSTEM_MAP = Object.fromEntries(SYSTEMS.map(s => [s.id, s]));
