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
  /** The whole spread of next-gameweek outcomes (backend distributions.py). */
  dist?: PointsDist | null;
}

/** A player's next-gameweek points distribution. Checked out of sample in
 *  backend/research/2026-10-distributions. */
export interface PointsDist {
  mean: number;
  /** 10th and 90th percentile scores: the likely range. */
  p10: number;
  p90: number;
  /** P(2 or fewer), P(6+), P(10+). */
  p_blank: number;
  p_return: number;
  p_haul: number;
  /** P(score = i) for i = 0, 1, 2, ... (negative scores folded into 0). */
  pmf: number[];
}

/** The armband as head-to-heads: the captain first, then the XI's next best. */
export interface CaptainOdds {
  player_id: number;
  name: string;
  projected: number;
  p_haul: number;
  p10: number;
  p90: number;
  /** P(he outscores the captain), ties left out, recalibrated. null for the captain. */
  beats_captain: number | null;
}

export type PlannedChip = "3xc" | "bboost" | "freehit";

export interface ChipWeek {
  gameweek: number;
  "3xc": number;
  "3xc_player": string | null;
  bboost: number;
  freehit: number | null;
  xi_points: number;
  /** Inside the transfer plan's horizon (the squad is known), not a held squad. */
  firm: boolean;
  fixtures?: { doubles: number; blanks: number } | null;
}

export interface ChipPlacement {
  chip: PlannedChip;
  gameweek: number;
  value: number;
  player: string | null;
  firm: boolean;
  now: boolean;
}

export interface ChipScenario {
  key: "free" | "wildcard";
  label: string;
  plan: ChipPlacement[];
  total: number;
  weeks: ChipWeek[];
  firm_through_gw: number;
}

/** Every chip you hold placed in its best week, with and without a Wildcard now. */
export interface ChipPlan {
  deadline_gw: number;
  gameweeks: number[];
  chips: PlannedChip[];
  scenarios: ChipScenario[];
}

export type NewsStatus = "out" | "doubtful" | "rotation_risk" | "expected_to_start" | "no_news";

export interface NewsItem {
  player_id: number | null;
  name: string;
  club: string;
  status: NewsStatus;
  start_chance: number | null;
  reason: string;
  source_url: string | null;
  source_date: string | null;
  /** The headline the call comes from. */
  source_title?: string | null;
}

/** What the team-news reader found for the players in this decision. */
export interface TeamNewsView {
  enabled: boolean;
  fetched_at?: string;
  model?: string;
  items: NewsItem[];
  /** Calls that lowered a projection (worse than FPL's own flag). */
  applied: { player_id: number; status: NewsStatus; chance: number; fpl_chance: number }[];
  errors?: number;
  /** The reader's record: each finished gameweek's calls against who played. */
  record?: NewsRecord | null;
}

export interface NewsRecord {
  gameweeks: number[];
  by_status: Record<NewsStatus, { calls: number; correct: number }>;
  recent: { gameweek: number; name: string; status: NewsStatus; minutes: number; started: boolean; correct: boolean }[];
  /** Rotation calls only move projections once this many were checked at this hit rate. */
  rotation_bar: { calls: number; rate: number };
}

/** A match outside the Premier League (backend other_matches.py). */
export interface OtherMatch {
  date: string;
  competition: string;
  opponent: string | null;
  home: boolean;
  /** Played outside Europe — a long trip back. */
  far: boolean;
}

/** Your players' cup, European and international games over the planning window. */
export interface OtherMatchesView {
  from: string;
  to: string;
  clubs: { club: string; players: string[]; matches: OtherMatch[] }[];
  international: { player_id: number; name: string; nation: string; matches: OtherMatch[] }[];
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

export interface ChipSuggestion {
  chip: "wildcard" | "bboost" | "3xc" | "freehit";
  gameweek: number;
  reason: string;
}

export interface ChipWatch {
  checked_through_gw: number;
  next_double_gw: number | null;
  next_blank_gw: number | null;
}

/** The best week inside the planning horizon to play an expiring chip. */
export interface ChipBestWeek {
  chip: ChipSuggestion["chip"];
  gameweek: number;
  /** Expected points the chip adds that week (captain again, or the bench). */
  value: number;
  player: string | null;
}

/** Chips come in half-season sets; an unplayed chip is lost at its deadline. */
export interface ChipExpiry {
  deadline_gw: number;
  gameweeks_left: number;
  chips_left: ChipSuggestion["chip"][];
  /** One chip per gameweek, so true once weeks left <= chips left. */
  urgent: boolean;
  best_weeks: ChipBestWeek[];
  visible_through_gw: number | null;
}

export interface LineupCheck {
  model_agrees: boolean;
  points_yours: number;
  points_model: number;
  model_would_start: string[];
  model_would_bench: string[];
  model_captain: string | null;
  model_vice_captain: string | null;
  /** Squad changes the model would still make (free until the deadline),
   *  only when worth suggested_gain >= 1 point over the horizon. */
  suggested_changes: {
    out: string;
    out_id: number;
    in: string;
    in_id: number;
    in_cost_m: number;
    out_points: number;
    in_points: number;
  }[];
  suggested_gain: number;
}

export interface TeamInfo {
  name: string;
  entry_id: number;
  bank_m: number;
  squad_value_m: number;
  free_transfers: number;
  chips_available: string[];
}

/** One player, and how many rivals ahead of you hold him. */
export interface RivalOwnership {
  player_id: number;
  name: string;
  /** His club (absent in files written before it was added). */
  team?: string;
  cost_m: number;
  owned_by: number;
  /** 0-1, as a share of the rivals ahead of you. */
  share: number;
}

export interface LeagueRival {
  entry: number;
  name: string;
  rank: number;
  total: number;
  is_you: boolean;
  chips: { chip: string; gameweek: number }[];
  hits_cost: number;
}

/** Ownership inside your actual mini-league — the number that decides whether
 *  a transfer gains you a PLACE, rather than just points. */
export interface LeagueView {
  league_id: number;
  league_name: string;
  league_size: number;
  your_rank: number | null;
  rivals_ahead: number;
  gameweek_read: number;
  differentials: RivalOwnership[];
  template_gaps: RivalOwnership[];
  chips_spent: LeagueRival[];
  /** The half-season chip set currently in play. */
  chip_window?: { start: number; end: number };
}

export interface WildcardPlayer {
  player_id: number;
  name: string;
  position: Player["position"];
  team: string;
  cost_m: number;
  predicted_points: number;
  horizon_points: number;
  starting: boolean;
  /** Not in your current squad. */
  new: boolean;
  /** How many of the managers ahead of you in your league start him. */
  owned_by_ahead: number;
}

/** A second look at a pick the model wants to buy (backend main._pick_checks). */
export interface PickCheck {
  player_id: number;
  name: string;
  /** Plain reasons: form far below the projection, price-led projection, benching risk. */
  flags: string[];
  wildcard: boolean;
  transfer: boolean;
  /** Six-week points lost by leaving him out of the Wildcard, and who comes in instead. */
  drop_cost?: number;
  replacement?: string[];
  /** Best like-for-like swaps: same position, affordable, club limit respected. */
  alternatives?: PickAlternative[];
}

export interface PickAlternative {
  player_id: number;
  name: string;
  team: string;
  cost_m: number;
  next: number;
  six_weeks: number;
  /** Points per game this season. */
  ppg: number;
  /** Six-week projection minus the flagged player's. */
  vs: number;
  /** The same checks, applied to him. */
  flags?: string[];
}

export interface WildcardOption {
  gameweek: number;
  /** Decay-weighted expected points over the six-week horizon, vs the free-transfer plan. */
  gain_six_weeks: number;
  points_with: number;
  points_without: number;
  changes: number;
  xi_m: number;
  bench_m: number;
  bank_m: number;
  captain_id: number;
  vice_captain_id: number | null;
  squad: WildcardPlayer[];
  rivals_ahead: number;
  free_alternative: { out: string[]; in: string[] };
  /** Picks worth a second look, with the cost of leaving each out. */
  checks?: PickCheck[];
}

export interface OptimizedTeam {
  generated_at: string;
  /** The deadline of `gameweek`, ISO time (absent in older files). */
  deadline?: string | null;
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
  /** Named, actionable chip suggestions inside the planning horizon. */
  chip_advice?: ChipSuggestion[];
  /** Whole-season DGW/BGW scan, so "nothing suggested" reads as watched, not silent. */
  chip_watch?: ChipWatch;
  /** When the chips you hold expire, and the best week in sight for each. */
  chip_expiry?: ChipExpiry;
  /** Your mini-league: who owns what, and who has spent which chips. */
  league?: LeagueView;
  /** The plan with a Wildcard played this gameweek, vs the free-transfer plan. */
  wildcard_option?: WildcardOption;
  /** Present when captain/vice are your own pick (backend/overrides.json)
   *  rather than the model's; holds what the model would have chosen. */
  captain_override?: { model_captain_id: number; model_vice_captain_id: number | null };
  /** A Wildcard or Free Hit you've played this gameweek, with the team you
   *  set in the FPL app (backend/overrides.json "team"): FPL keeps it private
   *  until the deadline, so the page shows your set team, not last week's. */
  active_chip?: { chip: "wildcard" | "freehit"; gameweek: number };
  /** Your set lineup against the model's best XI from the same 15. */
  lineup_check?: LineupCheck | null;
  /** The captain against the XI's next best options. */
  captain_odds?: CaptainOdds[];
  /** Head-to-head chances are recalibrated by this log-odds scale (backend
   *  distributions.PAIR_LOGIT_SCALE), so the page's own comparisons match. */
  odds_calibration?: { pair_logit_scale: number };
  /** Chip placement up to the chip deadline. */
  chip_plan?: ChipPlan;
  /** Team news for your squad, planned buys and the Wildcard squad. */
  team_news?: TeamNewsView;
  /** Cup, European and international games for the same players. */
  other_matches?: OtherMatchesView;
  /** Picks worth a second look: Wildcard newcomers and this week's buys. */
  pick_checks?: PickCheck[];
}
