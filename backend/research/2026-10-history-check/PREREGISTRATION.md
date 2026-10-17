# Is the old-season training data hurting the model THIS season? — pre-registration
Written 2026-10-17 12:51 MDT, before any run. Commit 0bb8895.

Why: the user's point — the past-season tests replay past seasons, so they
can't show whether old data misleads the model in 2026-27, where ratings are
stale and the season may differ. This replays 2026-27 itself, GW2-6 (GW1-6
complete in the 2026-10-15 snapshot), walk-forward, with the live pipeline,
changing only the training data:

- production: 2023-24, 2024-25, 2025-26 + this season (live)
- last_season: 2025-26 + this season
- this_season: this season only
- recency: production's data, older seasons down-weighted 0.7 a season

Seeds 42, 7, 13, 101, 2024; --bag-size 1. Primary: squad points over GW2-6,
paired by seed against production. Five gameweeks is a small sample, so this
is evidence, not a verdict by itself: a variant counts as "better this
season" only if it beats production on at least 4 of 5 seeds AND by 10+
points on average. If one does, it then goes through the usual past-season
test before going live; if none does, the old data stays.
