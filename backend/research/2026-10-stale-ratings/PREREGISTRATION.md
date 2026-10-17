# Training on stale team ratings, as the live model plays on them — pre-registration
Written 2026-10-17 12:11 MDT, before any run. Commit de0b3f7.

Why: FPL publishes no team ratings for 2026-27, so the live model plays every
match on last season's. But it learned from past seasons rated with their OWN
ratings, which may carry hindsight and are certainly fresher. It trusts a stale
rating as much as it learned to trust a fresh one. In GW7, "reputation" (price
plus team ratings) made up 42% of what moved the user's XI's points-if-he-plays,
against 32% across past seasons. Semenyo +2.7 and Cherki +2.6 from reputation,
+0.8 and +1.1 from this season's play; Raya +1.1 and -0.3.
(research/2026-10-lagged-team-form found the season's own ratings worth +107
[+17, +198] in 2025-26 when both training and replay had them.)

## Variants (backtest.py)
- live_ratings (reference): the live set-up. Seasons trained on keep their
  own ratings; the replayed season is rated with the season before's.
- lagged_ratings (candidate): every season rated with the season before's,
  training and replay alike, so the model learns what a stale rating is worth.
  Live, this is config.LAGGED_TEAM_RATINGS = True for the historical seasons.

## Primary — backtest, points
2025-26 replayed with 2024-25 as the prior season, seeds 42, 7, 13, 101, 2024,
--bag-size 1. (A season replayed without a prior has nothing else to train on,
so the two variants are identical there; 2024-25 alone can't tell them apart
and isn't run.)
ACCEPT only if the paired 95% CI is above zero. Then ONCE on 2023-24 with
2022-23 as prior, logged in config's "Uses so far"; ship only if > 0 there.
Anything else: not used, and the result goes in the ledger.
