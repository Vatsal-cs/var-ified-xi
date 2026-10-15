# Form adjusted for the opponent — pre-registration
Written 2026-10-15, before any run with these inputs.

Why: a player's recent form is a raw average, so three goals against
relegation sides count the same as three against the top four; in cup,
European and international games, goals against a League Two side or San
Marino count the same as against Bayern.

## Variants (data_engine/backtest.py), each added to the current production model
- **sched** — strength of the player's last five Premier League opponents
  (opp_def_avg_5, opp_att_avg_5), so the model can weigh form by schedule itself.
- **form_adj** — opponent-adjusted Premier League form: each match's xG, xGI
  and points scaled by the opponent's FPL strength relative to the average
  (attackers by its defence, defenders and keepers by its attack), averaged
  like the raw form (xg_adj_avg_5, xgi_adj_avg_3, points_adj_avg_5).
- **other_form_adj** — form in cup, European and international games weighted
  by opponent strength: clubs by an Elo built from every Champions/Europa/
  Conference League and English cup result since 2022 (pre-match ratings),
  national teams by eloratings.net's previous-year rating; weight
  10^((rating - reference)/800) capped to [0.2, 1.5]
  (xm_apps_30, xm_ga_adj_30, xm_shots_adj_30, xm_opp_30).

## Primary — backtest, points
production vs each variant, seeds 42, 7, 13, 101, 2024; 2024-25 (trained on
itself) and 2025-26 (plus 2024-25); gameweeks 2-38; --bag-size 1 both sides.
**ACCEPT** a variant only if "better" (pooled 95% CI above zero AND ahead in
both seasons); if several are, the largest pooled gain goes forward alone.
Then ONCE on 2022-23 and 2023-24 (5 seeds), logged in config's "Uses so
far"; ship only if > 0 in both. Otherwise production is unchanged.
