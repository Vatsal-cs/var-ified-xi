# Form in European, cup and international games — pre-registration
Written 2026-10-21 07:49 MDT, before any step is run.

Question (from the user): does how a player performs in Champions League,
Europa League, Conference League, cup and international games — and against
how strong an opponent — tell us anything about his next Premier League game
that the model doesn't already know?

History, stated up front: other_matches_form (goals + assists, shots, shots
on target in those games, last 30 days) was tested once: +81 [-4, +168],
ahead in 9 of 10 runs, not "better" (research/2026-10-other-matches). An
opponent-weighted version lost (-17). Production has changed since (ownership
shipped). This is a second look, so the bar does not move and the held-back
seasons still decide.

## Step 1 — is there a signal at all? (diagnostic, gates everything else)
Rows: research/2026-10-projection-bias rows_{2024-25,2025-26}_om.csv — every
player-gameweek with the model's walk-forward projection made before the
deadline — joined to the 30-day European/cup/international form columns
(xm_apps_30, xm_ga_30, xm_shots_30, xm_sot_30, xm_opp_30), computed from
matches strictly before each gameweek's deadline.
Population: midfielders and forwards projected 2.5+ with at least one such
appearance in the 30 days before (xm_apps_30 >= 1).
Statistic: mean residual (actual - projected) of players with a goal or
assist in those games (xm_ga_30 >= 1) minus those without (xm_ga_30 = 0).
95% interval by bootstrap over gameweeks, both seasons pooled; each season
also reported.
GO to step 2 only if the pooled difference is above zero with the 95% interval
excluding zero. Otherwise stop: European form adds nothing the model doesn't
already know, and nothing is built.
Descriptive only: the same split by opponent strength (xm_opp_30 above vs
below its median among those players) and by shots on target.

## Step 2 — points, the usual way (only if step 1 says GO)
production vs other_matches_form (production plus xm_apps_30, xm_ga_30,
xm_shots_30, xm_sot_30, and xm_opp_30 so the model can weigh opponent
strength), seeds 42, 7, 13, 101, 2024, 2024-25 and 2025-26, --bag-size 1.
ACCEPT only if "better": pooled 95% CI above zero AND ahead in both seasons.

## Step 3 — held-back seasons, once (only if step 2 ACCEPTs)
2022-23 and 2023-24, same settings; ship (behind a config switch) only if
ahead in both. Logged in config's "Uses so far" whatever it says.
