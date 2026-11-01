# The crowd's captain — pre-registration
Written 2026-11-01, before any run. Runs on GitHub Actions.

Why: the Canada top 20 (of 109,472) out-scored us by ~49 points on Haaland
alone over GW2-8, mostly the armband. They captained him in 58% of their
weeks; the model's captain (the XI's highest mean projection) was João
Pedro and Bruno Fernandes early on. The question is whether the crowd's
captain choice carries information the model's mean misses, judged on past
seasons' points, not on one season's hindsight.

## Variant (backtest.py "captain_crowd")
lagged_ratings with the same squad and XI. Only the armband changes: it goes
to the XI's most-owned player among those projected within 1.0 point of the
XI's best projection (ties to the higher projection). The model's own captain
becomes vice; if they agree, nothing changes. Ownership is the archive's
share of managers owning him that gameweek.

## Primary — backtest, points
captain_crowd vs lagged_ratings, seeds 42, 7, 13, 101, 2024; 2024-25 (trained
on itself) and 2025-26 (plus 2024-25); --bag-size 1.

- "Better" (pooled 95% CI above zero AND ahead in both seasons): ONE run on
  the held-back 2022-23 and 2023-24, logged in config's "Uses so far". It
  ships only if above zero in both.
- Anything else: the model keeps captaining on its own mean projection.

## Descriptive only
How many gameweeks the armband changes hands, and the captain points either
way.
