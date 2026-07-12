// File: types.ts
// Path: var-ified-xi/frontend/lib/types.ts
//
// Mirrors the exact JSON contract written by backend/main.py's
// build_output_json(). Keep this in sync if you change that function.

export interface Player {
  player_id: number;
  name: string;
  position: "GK" | "DEF" | "MID" | "FWD";
  team: string;
  now_cost_m: number;
  predicted_points: number;
  is_captain: boolean;
  is_vice_captain: boolean;
}

export interface OptimizedTeam {
  generated_at: string;
  gameweek: number | null;
  budget_used_m: number;
  budget_total_m: number;
  predicted_total_points: number;
  starting_xi: Player[];
  bench: Player[];
  captain_id: number;
  vice_captain_id: number | null;
}
