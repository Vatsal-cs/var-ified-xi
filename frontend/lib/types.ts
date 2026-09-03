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
  /** Expected points in the upcoming gameweek alone. */
  predicted_points: number;
  /** Decay-weighted expected points across the whole planning horizon. */
  horizon_points: number;
  /** Expected points keyed by gameweek number, e.g. { "2": 6.78, "3": 6.34 }. */
  xp_by_gw: Record<string, number>;
  /** Model's probability the player plays 60+ minutes. */
  start_probability: number;
  is_captain: boolean;
  is_vice_captain: boolean;
}

/** One player moving in or out in a planned transfer. */
export interface TransferMove {
  player_id: number;
  name: string;
  position: Player["position"];
  team: string;
  predicted_points: number;
  cost_m?: number;
  sell_price_m?: number;
}

export interface PlannedWeek {
  gameweek: number;
  transfers_in: TransferMove[];
  transfers_out: TransferMove[];
  transfer_count: number;
  free_transfers: number;
  hits: number;
  hit_cost: number;
  bank_m: number;
  predicted_points: number;
  captain_id: number | null;
}

export interface HitRecommendation {
  worth_it: boolean;
  hit_cost: number;
  net_gain_over_horizon: number;
  extra_transfers_in: TransferMove[];
  extra_transfers_out: TransferMove[];
  verdict: string;
}

export interface TeamInfo {
  name: string;
  entry_id: number;
  bank_m: number;
  squad_value_m: number;
  free_transfers: number;
  chips_available: string[];
}

export interface OptimizedTeam {
  generated_at: string;
  gameweek: number | null;
  horizon_gws: number;
  /** "fresh_squad" builds from scratch; "transfer_plan" works from your real team. */
  mode: "fresh_squad" | "transfer_plan";
  budget_used_m: number;
  budget_total_m: number;
  predicted_total_points: number;
  starting_xi: Player[];
  bench: Player[];
  captain_id: number;
  vice_captain_id: number | null;
  /** Present only in transfer_plan mode. */
  transfer_plan?: { weeks: PlannedWeek[]; hit_recommendation?: HitRecommendation | null };
  /** Present only in transfer_plan mode. */
  team?: TeamInfo;
}
