# Planner horizon decay 0.95 — pre-registration
Written 2026-10-26 MDT, before any run.

## Why
Against the same model with unlimited transfers (backtest), the
transfer-constrained simulator gives up 3.8 (2025-26) and 6.7 (2024-25)
points a gameweek in normal weeks, plus 13-18 in blank/double weeks, which
are chip weeks the simulator doesn't play (research/2026-10-top-gap).

`HORIZON_DECAY = 0.85` was set by argument and never tested: week 6 of the
plan counts 44% of next week. With one free transfer a week a player bought
is typically held for 10+ weeks, so the planner may undervalue players who
stay good beyond the next couple of fixtures and over-trade for short runs.
One candidate, chosen for that reason before any run: 0.95 (week 6 = 77%).

## Policy (season_sim.py "production_decay95")
The shipping procedure with 0.95 in both planner solves and in the hit
check's comparison. Candidate pools and everything else unchanged.

## Primary — simulator, paired branch test
production:production_decay95, GW2-38, seeds 42, 7, 13; 2024-25 and 2025-26
(2025-26 trained with 2024-25), --bag-size 1, cloud workflow. ACCEPT only if
"better" (pooled 95% CI above zero AND ahead in both seasons; block 4). Then
ONCE on 2022-23 and 2023-24 (same design), logged in config's "Uses so far";
ship only if > 0 in both. Otherwise HORIZON_DECAY stays 0.85.
