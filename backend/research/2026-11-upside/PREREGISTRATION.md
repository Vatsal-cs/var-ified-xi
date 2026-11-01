# Upside mode — pre-registration
Written 2026-11-01, before any run. Runs on GitHub Actions.

Why: the user's goal is a top-10 world finish, not the best average. The
model maximises expected points, which gives a good typical finish but plays
it safe. Reaching an extreme rank needs more big seasons, which means
backing upside: players and captains with a higher "good day", accepting
more bad weeks. This measures that trade directly.

## Variants (backtest.py), each lagged_ratings with the same model
- upside_captain: armband on the 80th-percentile good-day projection
  (config.CAPTAIN_QUANTILE); squad and XI unchanged. (Tried once in the old
  harness, −8 on average; never measured for big seasons.)
- upside_half: squad, XI and armband picked on the mean projection pulled
  halfway to the good-day projection.
- upside_full: all picked on the good-day projection.

## Measures
- Huge-season chance (research/2026-11-upside/tail.py): seasons rebuilt from
  each run's weekly scores by drawing two-gameweek blocks with replacement
  (paired: same blocks and seed for every variant, 20,000 draws per season).
  "Huge" = the reference's own top 1% of those seasons, so the reference
  scores 1% by construction.
- Average: the usual paired backtest result.

Seeds 42, 7, 13, 101, 2024; 2024-25 (trained on itself) and 2025-26 (plus
2024-25); --bag-size 1.

## Decision
A variant passes if its huge-season chance is at least 2.0% (double) in BOTH
seasons AND its average costs no more than 50 points in each season. Of
those that pass, the one with the highest pooled chance goes ONCE to the
held-back 2022-23 and 2023-24 with the same test (logged in config's "Uses
so far"). It ships as the default only if it passes there too. Otherwise the
model stays on the mean, and the answer is that chasing upside doesn't buy
enough big seasons.

Limitation, stated up front: the backtest rebuilds the squad every week with
unlimited transfers, and the "huge" line is relative to our own model's
seasons, not the field's. This measures how much the model's own spread
widens, which is a necessary condition for a better shot at an extreme rank,
not proof of one.

## Addendum, 2026-11-01, after the tuning run (a declared deviation)
Tuning result: no variant passed. upside_full came closest: huge-season
chance 1.80% (2024-25) and 2.56% (2025-26), against 2.0% needed in both,
with no cost on average (+0 and +49, pooled +49 [−89, +204]). By the rule
above, the model stays on the mean.

Because its average cost looks like zero, upside_full alone gets ONE look at
the held-back 2022-23 and 2023-24. This is not in the original plan, and
it's written here before that run. Same test there: huge-season chance at
least 2.0% in both held-back seasons AND average cost no more than 50 in
each. It ships as the default only if it passes both. Otherwise it is
closed. This is a second bite at a failed variant, so it ships only if the
evidence is clean in both new seasons.
