# Step 3 (E4) — pre-registration
Written 2026-10-08 20:21 MDT, before any full run. Code: horizon_availability.py as committed with this file.

Change: injured/suspended players' weeks AFTER next valued by horizon_availability
(suspension served -> 0.9; dated suspension -> out until the date; injury with
date -> out >14 days before it, 0.2 within 14 days, 0.8 from it; undated injury
-> 0.25/0.40/0.50/0.60/0.65 for +1..+5). Next gameweek untouched.

Primary test — paired branch evaluation (season_sim --branch production:production_e4):
each gameweek production_e4 decides from production's exact position; both
decisions are scored on realised points over the next 6 gameweeks holding the
squad (later XIs/armbands from the deadline's projections), hits deducted.
Seasons 2024-25, 2025-26; seeds 42, 7, 13; block bootstrap, 6-GW blocks.

ACCEPT (set config.HORIZON_AVAILABILITY = True) only if:
  (1) the pooled paired difference's 95% CI is above zero, AND
  (2) the difference is positive in BOTH seasons, AND
  (3) the full-season simulation verdict for production_e4 vs production is not "worse".
Otherwise it stays off and is recorded with its numbers.

No back-season confirmation is possible (flags start 2024-25); the live 2026-27
season is the holdout. The factors were read off these two seasons' return
rates (same in both) — disclosed, not tuned against points.
commit 91ac9cf
