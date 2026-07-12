// File: getTeamData.ts
// Path: var-ified-xi/frontend/lib/getTeamData.ts
//
// Reads the static JSON produced by the local backend engine.
// This runs at build/request time on the server — no API route needed
// since main.py already writes the file straight into public/.

import fs from "fs";
import path from "path";
import type { OptimizedTeam } from "./types";

export function getTeamData(): OptimizedTeam | null {
  const filePath = path.join(process.cwd(), "public", "optimized_team.json");
  if (!fs.existsSync(filePath)) return null;

  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as OptimizedTeam;
  } catch {
    return null;
  }
}

// Formation-shape derivation, used to lay out the pitch (e.g. "3-4-3")
export function deriveFormation(startingXi: OptimizedTeam["starting_xi"]) {
  const counts = { DEF: 0, MID: 0, FWD: 0 };
  for (const p of startingXi) {
    if (p.position === "DEF") counts.DEF++;
    if (p.position === "MID") counts.MID++;
    if (p.position === "FWD") counts.FWD++;
  }
  return `${counts.DEF}-${counts.MID}-${counts.FWD}`;
}
