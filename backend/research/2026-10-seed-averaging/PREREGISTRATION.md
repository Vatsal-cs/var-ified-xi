# Seed averaging — pre-registration
Written 2026-10-08 22:00 MDT, before any run.

Change: config.MODEL_BAG_SIZE = 5 — five copies of the two-stage model, seeds
MODEL_SEED + 7919*i, projections and play probabilities averaged before the
availability adjustments.

Purpose: steadier picks (one seed currently moves a two-season backtest by up
to ~175 points), at no cost in points or accuracy. So this is a
non-inferiority-plus-stability test, not a "more points" test.

Primary — backtest, production vs bagged5, run seeds 42, 7, 13, 101, 2024,
tuning seasons 2024-25 and 2025-26 (paired per run seed; bagged5's first
member IS that seed's production model).

ACCEPT on the tuning seasons only if ALL hold:
  (1) points: the verdict is not "worse" AND the pooled paired difference >= 0;
  (2) accuracy: MAE no worse than production by more than 0.002, and Brier
      P(60+) by more than 0.0005, in EACH season;
  (3) stability: mean pairwise starting-XI overlap between run seeds (same
      gameweek) is higher for bagged5 in EACH season, and pooled captain
      agreement between run seeds is higher.
If accepted, confirm ONCE on 2022-23 and 2023-24 (5 seeds): ship
(MODEL_BAG_SIZE = 5) only if (1) and (3) also hold there.

Secondary, descriptive only: on today's live data, agreement of this week's
recommended transfer and captain across 6 independent single models vs 6
independent bags.
commit 4edf1ec
