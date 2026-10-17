# Early-season tilt toward points per match played — pre-registration
Written 2026-10-17 13:13 MDT, before any run. Commit 75b53ea.

Why: the model's six-week projections sit in a tight band and barely follow
what players have scored this season. GW7 2026-27: Sávio (10 points, 65
same-price midfielders have more) projected 18.7 over six weeks, De Cuyper
(53 points) 14.0, João Pedro (47) 12.4. In the projection-bias rows, the best
extra weight on points per match played over the last five was positive in
the first ten gameweeks of every season looked at: 2024-25 +0.17, 2025-26
+0.10, 2026-27 +0.22 (rows projected 2.5+, 3+ of the last 5 played); over
whole seasons +0.11 and +0.01.

## Variant (backtest.py "form_tilt")
production, then for target gameweeks 1-10 only, players with 3+ of the last
five played and projected 2.5+: projection + w x (points per match played over
the last five - projection). w is fitted on the OTHER tuning season: 0.10 when
replaying 2024-25 (from 2025-26), 0.17 when replaying 2025-26 (from 2024-25);
0.135 (the mean) for the held-back seasons and live.

## Primary — backtest, points
production vs form_tilt, seeds 42, 7, 13, 101, 2024; 2024-25 (trained on
itself) and 2025-26 (plus 2024-25); --bag-size 1. ACCEPT only if "better"
(pooled 95% CI above zero AND ahead in both seasons); then ONCE on 2022-23 and
2023-24, logged in config's "Uses so far"; ship (live, w = 0.135, GW <= 10)
only if > 0 in both. It only touches ten gameweeks a season, so a real effect
may still not reach the bar.
