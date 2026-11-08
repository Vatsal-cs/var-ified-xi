// File: freeHit.ts
// Path: var-ified-xi/frontend/lib/freeHit.ts
//
// When the chip plan says to play your Free Hit this week, its team is the
// week's call (backend main._free_hit_payload): the page shows it in place of
// your own XI, so the headline, the pitch and the email all say the same.

import type { FreeHitTeam, OptimizedTeam } from "./types";

export function freeHitNow(team: OptimizedTeam): FreeHitTeam | null {
  const fh = team.free_hit;
  if (!fh?.play || fh.gameweek !== team.gameweek || team.active_chip) return null;
  return fh;
}

/** The team as the page shows it this week: the Free Hit team when that's the call. */
export function weekTeam(team: OptimizedTeam): OptimizedTeam {
  const fh = freeHitNow(team);
  if (!fh) return team;
  return {
    ...team,
    starting_xi: fh.starting_xi,
    bench: fh.bench,
    captain_id: fh.captain_id,
    vice_captain_id: fh.vice_captain_id,
    predicted_total_points: fh.points,
    // Both describe your own XI's armband, not this one's.
    captain_odds: undefined,
    captain_override: undefined,
  };
}
