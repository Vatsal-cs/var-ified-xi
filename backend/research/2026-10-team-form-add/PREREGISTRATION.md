# This season's team form, added to the ratings — pre-registration
Written 2026-10-15, before any run.

Why: the live model rates teams by last season's FPL ratings (FPL publishes
none for 2026-27). Six games in, the table disagrees sharply — Brighton 3rd
with 18 scored, Brentford and Everton unbeaten; Spurs 18th with 3 scored,
Villa 16th, Bournemouth 19th. The earlier test REPLACED the ratings with
recent-xG team form and lost (research/2026-10-team-form). This one ADDS the
same team-form inputs and keeps the ratings, so the model learns how much to
trust each as the season goes on.

## Variant (backtest.py "team_form_add")
production (with the shipped other-matches inputs) plus team_form.py's
columns: team_xg_for, team_xg_against, opp_xg_for, opp_xg_against,
match_xg_for, match_xg_against (recency-weighted, from matches strictly
before; prior = last season's rating halfway to the league mean, worth four
matches; promoted clubs = the relegated clubs' average).

## Primary — backtest, points
production vs team_form_add, seeds 42, 7, 13, 101, 2024; 2024-25 (trained on
itself) and 2025-26 (plus 2024-25); --bag-size 1. ACCEPT only if "better"
(pooled 95% CI above zero AND ahead in both seasons); then ONCE on 2022-23
and 2023-24, logged in config's "Uses so far"; ship only if > 0 in both.
Descriptive: the 2026-27 GW2-6 replay.
