# Early-season after-a-haul correction — pre-registration
Written 2026-11-21, before any run. Runs on GitHub Actions.

Why: the November 2026 model audit (research/2026-11-model-audit) replayed
the current model walk-forward on 2023-24, 2024-25, 2025-26 and 2026-27
GW2-10. Players projected 3+ straight after a 10+ point match, in GW2-14,
scored less than projected in every season: −0.88 (2023-24), −1.18
(2024-25), −0.91 (2025-26), −0.20 (2026-27, GW2-10). Among each week's top
10 projections the miss for these players is −1.7 to −2.6, against −0.3 to
−0.8 for the rest. The October audit (research/2026-10-top-gap) saw the
same pattern in two seasons and tied it to the worst hits in the
simulator. Earlier general fixes (early-season shrinkage, matches_played,
a residual model) did not target it.

Declared peek: the audit looked at 2023-24, a held-back season,
descriptively. 2022-23 is the only untouched held-back season.

## Variant (backtest.py)
- haul_dampen: lagged_ratings, but a player whose last match scored 10+
  (points_avg_1, the previous match only) has k points taken off his
  projection, floored at 0, in GW14 and earlier. k is the miss measured on
  the OTHER tuning season, never the season being replayed: 0.91 for
  2024-25 (from 2025-26), 1.18 for 2025-26 (from 2024-25), 1.05 (their
  average) for 2022-23 and 2023-24. Captaincy uses the corrected projection.
- Reference: lagged_ratings.

## Run
Seeds 42, 7, 13, 101, 2024. Seasons 2024-25 (trained on itself) and 2025-26
(plus 2024-25). --bag-size 1. Pooled with data_engine.evaluation,
--reference lagged_ratings, --block 4. Same run as points_by_part
(research/2026-11-components), sharing the reference.

## Decision
- Ahead in BOTH tuning seasons and the pooled 95% interval above zero:
  ONE run on the held-back seasons, with 2022-23 as the deciding one (the
  untouched season) and 2023-24 reported. It ships only if it is ahead in
  2022-23 and not behind in 2023-24.
- Anything else: not used, recorded as a rejected variant with its numbers.

Limitation stated up front: the backtest rebuilds the squad every week, so
it can't see the transfer harm the October audit found (buying a player
after a haul, then selling him). It can only see the projection and
captaincy effect. A pass here would be followed by the season simulator.
