# No hits before GW9 — pre-registration
Written 2026-10-26 MDT, before any run of this policy.

## Why
- 2026-27: "the model picks a player because he just scored 10". Out-of-sample
  rows (research/2026-10-projection-bias) agree for the early season only:
  players projected 2+ straight after a 10+ haul scored less than projected
  in every early bucket of both seasons (GW2-14: −1.20, −0.59, −1.77, −0.18
  in 2024-25; −0.58, −0.60, −0.99, −0.86 in 2025-26; n 14-85 each), and were
  calibrated after GW14 (+0.05, +0.18). The top 40 projections each week ran
  0.4-1.3 high in GW2-8 of 2024-25 and 1.0 high in GW2-3 of 2025-26.
- A hit is the decision that trusts a projected gain most. In the harness-v2
  simulator runs, following the hit advice in GW2-7 cost 58-72 points in all
  three 2024-25 seeds (GW3 alone −33/−42/−45) and −15 to +28 in 2025-26.
  Replayed: in GW3 2024-25 the model projected De Bruyne at 10.5 after his
  start and took a hit for him (GW3: 43 points with the hit, 80 without).

**Not independent of the tuning seasons:** the 2024-25 numbers above are why
this is being tested, so a tuning-season win is expected and proves little.
The held-back seasons are the real test.

## Policy (season_sim.py "production_early_nohits")
The shipping procedure, with hit advice ignored before GW9 (free transfers
unchanged); identical from GW9.

## Primary — simulator, paired branch test
production:production_early_nohits, GW2-8 (`--end-gw 8`; later decisions
are identical by construction), seeds 42, 7, 13; 2024-25 and 2025-26
(2025-26 with --prior-seasons 2024-25), --bag-size 1. Each decision scored
over the next six gameweeks from the same position.

ACCEPT only if "better" by the usual rule (pooled 95% CI above zero AND ahead
in both seasons). Then ONCE on 2022-23 and 2023-24 (same design), logged in
config's "Uses so far"; ship only if > 0 in both. Otherwise production keeps
following hit advice from GW2 and the result is recorded.
