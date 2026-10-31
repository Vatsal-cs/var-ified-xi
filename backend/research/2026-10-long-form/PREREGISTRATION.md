# Long-run form averages — pre-registration
Written 2026-10-31, before any run.

Why: the model's form inputs only look back three and five gameweeks
(config.ROLLING_WINDOWS = [3, 5]), plus FPL's own "form" (also five). There
is no longer view of a player at all, so a good player in a cold month and a
poor one on a hot run can look alike. The user's complaint (GW9) was exactly
that. The evidence so far is thin: in 2025-26, players coming off a cold run
outscored their projection by about +0.3 a match, but 2024-25 showed no clear
pattern. Putting more weight on recent form (form-tilt) lost 18 points. Giving
the model a longer view has never been tested.

## Variants (backtest.py)
- lagged_ratings (reference): production with each past season's teams
  rated on the previous season's FPL ratings, as the live model runs in
  2026-27.
- lagged_long_form: lagged_ratings plus ten inputs (points, minutes, xGI, BPS
  and defensive contributions), each averaged over the last ten gameweeks
  (`*_avg_10`) and over every earlier gameweek of the season (`*_avg_season`).
  Training rows exclude their own match; prediction rows include the latest
  match, as the existing windows do (feature_engineering.LONG_WINDOWS).

## Primary — backtest, points
lagged_long_form vs lagged_ratings, seeds 42, 7, 13, 101, 2024; 2024-25
(trained on itself) and 2025-26 (plus 2024-25); --bag-size 1.

- "Better" (pooled 95% CI above zero AND ahead in both seasons): run ONCE on
  the held-back 2022-23 and 2023-24 (same variants and seeds), logged in
  config's "Uses so far". Ship only if it is above zero in both.
- Anything else: not shipped. The long-run inputs stay built (they cost
  nothing live) but are not model inputs, and the answer to "it chases the
  last few games" is that a longer view doesn't score more points.

## Descriptive only
MAE and rank correlation by season; the new inputs' share of the stage-2
model's gain. Nothing is decided from these.
