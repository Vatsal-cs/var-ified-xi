# Club rotation rate, and calibrated points-if-60+ — pre-registration
Written 2026-10-20 14:50 MDT, before any run.

Why (GW7 2026-27 audit): City started 55% of the players the model gave 82%
(the minutes model only knows each player's own record, never that his manager
rotates); and the top of points-if-60+ runs high (players projected 7.95 if
they played scored 6.23; expensive attackers -1.3 in GW7).

## Variants (backtest.py), each against production
- team_rotation: plus team_changes_avg5 — starters changed from the previous
  match, averaged over the club's last five, as an input to both models.
  (2026-27 so far: Spurs 3.8, Chelsea 3.0, City 3.0 ... Bournemouth 0.6.)
- calibrated: points-if-60+ mapped through the smoothed distribution groups'
  real averages (what players projected at each level actually scored), the
  curve fitted on the OTHER tuning season's walk-forward rows; held-back
  seasons use both. Unlike the rejected linear shrink, this only bends where
  the projections ran high.

## Primary — backtest, points
Seeds 42, 7, 13, 101, 2024; 2024-25 (trained on itself) and 2025-26 (plus
2024-25); --bag-size 1. Each variant judged on its own: ACCEPT only if
"better" (pooled 95% CI above zero AND ahead in both seasons); then ONCE on
2022-23 and 2023-24, logged in config's "Uses so far"; ship only if > 0 in both.
