# Stale FPL ratings replaced by odds-based ratings — pre-registration
Written 2026-10-20 14:50 MDT, before any run.

Why: Brighton have outscored their projections every week of 2026-27 (+2.7 a
player-match GW2-6, +4.0 in GW7) under last season's ratings. Earlier tests
ADDED this season's xG or odds-based form to the stale ratings (no effect) or
replaced the ratings with xG form on hindsight-rated seasons (lost). This
REPLACES the stale ratings with odds-based ratings in the live set-up.

## Variants (backtest.py)
- lagged_ratings (reference): past seasons rated with the previous season's
  FPL ratings, as live.
- lagged_market_replace: the same, with team_strength_attack/defence,
  opp_strength_attack/defence and fixture_difficulty replaced by team_form.py's
  columns built from the goals the betting odds expected before each match
  (config.TEAM_FORM_SOURCE = "odds"), recency-weighted, prior = last season's
  final market rating pulled halfway to the mean.

## Primary — backtest, points
lagged_market_replace vs lagged_ratings, seeds 42, 7, 13, 101, 2024; 2024-25
and 2025-26 (plus 2024-25); --bag-size 1. ACCEPT only if "better"; then ONCE on
2022-23 and 2023-24; ship (odds-based ratings live) only if > 0 in both.
