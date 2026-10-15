# A second model that learns the first one's mistakes — pre-registration
Written 2026-10-15, before any backtest with it. (Before the first full run:
points_avg_3 dropped from the inputs — the walk-forward rows don't record it.)

Why: out of sample, the model's misses depend on the kind of player — e.g.
expensive players in poor recent form score +0.34 a match more than projected
([+0.12, +0.54]), expensive players in good form −0.15
(research/2026-10-projection-bias rows_*_om.csv, the shipped model). A
second, small model trained on those misses can correct each projection from
the player's current price, form, chances and minutes — no fixed lists, so a
player's correction changes as his form does.

## Corrector (fit_corrector.py)
XGBoost regressor, depth 3, 200 trees, learning rate 0.05, min_child_weight
50, subsample 0.8, target = actual − projected per player-match, inputs:
projected points, now_cost, element_type, points_avg_5,
xgi_avg_3, minutes_avg_3, starts_avg_3, dc_avg_5. Trained only on OTHER
seasons' walk-forward misses: simulating 2024-25 uses a corrector fitted on
2025-26's, simulating 2025-26 uses 2024-25's; the held-back seasons and live
use one fitted on both. Applied as projection + correction, floored at 0, to
every match projection (so it moves transfers, the XI and the captain) —
except projections under 0.5 (injured, suspended, not playing), which are
left alone so a correction can't revive an unavailable player.

## Primary — backtest, points
production vs **residual**, seeds 42, 7, 13, 101, 2024; 2024-25 (trained on
itself) and 2025-26 (plus 2024-25); --bag-size 1. ACCEPT only if "better"
(pooled 95% CI above zero AND ahead in both seasons); then ONCE on 2022-23
and 2023-24, logged in config's "Uses so far"; ship only if > 0 in both.
