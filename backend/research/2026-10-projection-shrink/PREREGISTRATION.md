# Pulling the top projections back — pre-registration
Written 2026-10-14 21:08 MDT, before any full run (a 4-gameweek smoke test
checked only that the variants run).

Why: out of sample, the points-if-60+ projection is too spread out. Players it
projects 8+ when they play scored ~6.6-6.8; those it projects ~2.4 scored
~2.9 (research/2026-10-distributions). The top projections are mostly the
expensive players, so this could be what tilts the squad toward big names
over cheaper in-form players.

## Change (train_model._shrink, config.CONDITIONAL_SHRINK)
projection -> m + k * (projection - m), where m is the position's average
60+ minute score in the training data. Only the points-if-60+ part changes;
the minutes model is untouched.

k is the within-position regression slope of real score on projection, from
the walk-forward rows of research/2026-10-projection-bias (single-match
gameweeks, 60+ minutes), always fitted on OTHER seasons than the one being
simulated (backtest.SHRINK_BY_SEASON):
- simulating 2024-25: k from 2025-26 = 0.687
- simulating 2025-26: k from 2024-25 = 0.596
- held-back seasons and live: k from both = 0.654
Per position (secondary): from 2025-26 {GK .552, DEF .813, MID .634, FWD .582},
from 2024-25 {GK .279, DEF .626, MID .655, FWD .443}, from both
{GK .362, DEF .759, MID .657, FWD .509}.

## Primary — backtest, points
production vs **shrink** (one k), seeds 42, 7, 13, 101, 2024; 2024-25 (trained
on itself) and 2025-26 (plus 2024-25); gameweeks 2-38; injury flags on;
--bag-size 1 both sides. Pooled with data_engine.evaluation.
**shrink_pos** (per-position k) is secondary.

**ACCEPT** on the tuning seasons only if the verdict is "better" (pooled 95%
CI above zero AND ahead in both seasons); if both variants are better, the
larger pooled gain goes forward. Then run it ONCE on 2022-23 (trained on
itself) and 2023-24 (plus 2022-23), 5 seeds, logged in config's "Uses so
far"; ship (set config.CONDITIONAL_SHRINK to the from-both factor) only if
the paired difference is > 0 in both. Otherwise it stays off, recorded
either way.

## Descriptive only
MAE, rank correlation, Brier P(60+); the 2026-27 GW2-6 replay (seeds 42, 7,
13, from-both factor).
