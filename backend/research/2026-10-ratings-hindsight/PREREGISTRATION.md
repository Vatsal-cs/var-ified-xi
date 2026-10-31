# How much of the stale-ratings gap is hindsight — pre-registration
Written 2026-10-31, before any run.

Why: the live model rates teams with last season's FPL ratings (FPL publishes
none for 2026-27). Replays put the cost at about −93 to −107 points a season
(research/2026-10-stale-ratings, research/2026-10-lagged-team-form), measured
against "production", which rates every past match with that season's
teams.csv from the archive.

That file is not what FPL showed at the time. FPL revises its ratings during
a season and the archive keeps only the last version. Its git history has
every saved version: 17 for 2024-25, 12 for 2025-26. In 2025-26 nothing
changed until 1 November 2025, then Liverpool's attack went 1310 -> 1160 and
Man Utd's defence 1120 -> 1275 by the end. Production rates GW1 with
end-of-season knowledge, so part of its edge is hindsight that no live model
has, and the "~100 points" may mostly be that.

## Variants (backtest.py)
- lagged_ratings (reference): every past season rated with the previous
  season's final ratings, as live in 2026-27.
- pit_ratings: every past match rated with the version of that season's
  teams.csv the archive committed before its kickoff (committer time), so
  never later than FPL showed it. This is the best a live model could have
  done in a season when FPL publishes ratings.
- production (descriptive only): the season's final file.

## Primary — backtest, points
pit_ratings vs lagged_ratings, seeds 42, 7, 13, 101, 2024; 2024-25 (trained
on itself) and 2025-26 (plus 2024-25); --bag-size 1.

- "Better" (pooled 95% CI above zero AND ahead in both seasons): FPL's
  ratings as shown at the time carry real information the live model lacks.
  Next step is a live stand-in for them, pre-registered separately.
- Anything else: the gap was mostly hindsight. Team-ratings work stops, and
  the "~100 points" figure is corrected wherever it is quoted.

## Descriptive only
production vs pit_ratings: the part of the old gap that was hindsight.
Nothing else is decided from this run.
