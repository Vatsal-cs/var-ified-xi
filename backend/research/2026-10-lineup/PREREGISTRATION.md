# Choosing the XI after autosubs — pre-registration
Written 2026-10-26 MDT, before any full run (one 7-week smoke test of the
backtest wiring, 2025-26 seed 42 stride 6: −12, one coin-flip swap).

## Why
2026-27 GW2-7: you lost 10.8 points a gameweek to the best XI from your own
15 in hindsight; top-10k managers 6.0 (research/2026-10-top-gap §3).

Every optimizer here picks the XI on expected points, which values a benched
player at (almost) nothing. That's right for a player who never comes on and
wrong for the first sub behind a rotation risk: starting a 60% starter worth
6 when he plays, with a sure 4 on the bench, expects 5.2; starting the sure
one expects 4. Expected points calls it the other way (3.6 vs 4). Bench order
already uses play chance (main.order_bench); the XI itself never has.

## Rule (data_engine/lineup.py)
From the squad as decided, every legal XI and bench order is valued by
expected points after FPL's autosub rule (4,000 simulated play/no-play draws,
independent per player, P(plays) = 1 − P(DNP) after the availability rule;
points given he plays = xP / P(plays)), and the best is fielded. The armband
goes on the top projections as production does. Squads, transfers and every
later decision are unchanged, so each week is a paired comparison with no
model noise.

## Primary — simulator, paired per gameweek
`season_sim --policies production --lineup`, production@lineup vs production,
seeds 42, 7, 13; 2024-25 and 2025-26 (2025-26 with --prior-seasons 2024-25),
--bag-size 1, GW2-38. ACCEPT only if "better" (pooled 95% CI above zero AND
ahead in both seasons). Then ONCE on 2022-23 and 2023-24 (same design),
logged in config's "Uses so far"; ship only if > 0 in both.

## Secondary — backtest (reported, not decisive)
`backtest --variants production --lineup`, 5 seeds × both seasons. Its
squads are rebuilt weekly with near-certain starters, so few weeks differ;
it checks the rule does no harm where rotation risk is rare.
