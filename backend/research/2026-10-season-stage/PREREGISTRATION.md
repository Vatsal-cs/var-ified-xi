# Season stage (matches_played) as a model input — pre-registration
Written 2026-10-26 MDT, before any run. Commit f2ce959.

## Why
Players projected 2+ straight after a 10+ haul scored less than projected in
every GW2-14 bucket of 2024-25 and 2025-26 (−0.2 to −1.8 a match), and were
calibrated after GW14 (research/2026-10-top-gap §4). The form windows (last
3 and 5 rows) look the same to the model whether they hold one match of this
season or five, so one early haul carries the weight of a run of form.

`matches_played` (fixtures so far this season: training rows count the rows
before the match, live rows the rows so far) is already built and was left
out after one seed on the pre-audit harness (4545 vs 4587, inside the ±146
seed noise). This re-measures it properly.

## Variant (backtest.py "season_stage")
Production plus matches_played as an input.

## Primary — backtest, points
production vs season_stage, seeds 42, 7, 13, 101, 2024; 2024-25 (trained on
itself) and 2025-26 (plus 2024-25); --bag-size 1. ACCEPT only if "better"
(pooled 95% CI above zero AND ahead in both seasons); then ONCE on 2022-23
and 2023-24, logged in config's "Uses so far"; ship only if > 0 in both.

## Secondary (reported)
Points in GW2-14 alone, where the effect should sit; MAE, rank correlation.
