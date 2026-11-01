# Five model changes, tested together — pre-registration
Written 2026-10-31, before any run. All runs on GitHub Actions
(`.github/workflows/backtest.yml`).

Why: long-run form just shipped (+102, held back +42/+19). These are the
remaining cheap ideas that need no new data source. Each is tested alone
against the current model, so the five verdicts are independent.

## Variants (backtest.py), each = lagged_ratings plus one change
- lagged_ratings (reference): production as live in 2026-27 (last season's
  team ratings, long-run form on).
- form_trend: breakout inputs. xGI, minutes and points over the last three
  gameweeks minus the season level (`*_trend`). Trees split on one input at a
  time, so "well above his own norm" is hard to build from two averages.
- per90: season-so-far points, xGI, BPS and defensive contributions per 90
  minutes played (zero below 450 minutes). A per-gameweek average mixes
  quality with how often he plays.
- long_form_rest: ten-gameweek and season windows for starts, xG, xA, clean
  sheets, saves and xGC (the stats long-run form left out).
- last_season: each player's previous Premier League season. Minutes, and
  points, xGI and BPS per 90 (zero below 900 minutes), from the archive's
  players_raw.csv on FPL's lifetime player code. Zero for anyone new.
  (Live would map bootstrap `code` to last season's players_raw. That is
  built only if it ships.)
- deeper_trees: trees six deep instead of four in the minutes and points
  models (config.TREE_MAX_DEPTH). Four was never tested against anything.

## Primary — backtest, points
Each variant vs lagged_ratings, seeds 42, 7, 13, 101, 2024; 2024-25 (trained
on itself) and 2025-26 (plus 2024-25); --bag-size 1.

- "Better" (pooled 95% CI above zero AND ahead in both seasons): goes to ONE
  confirmation run on the held-back 2022-23 and 2023-24, all passing variants
  in that same run, logged in config's "Uses so far". Each ships only if it
  is above zero in both held-back seasons.
- Anything else: not shipped. Columns stay built, not model inputs; the
  depth stays 4.
- If two or more ship: their combination is run once on the tuning seasons
  and ships only if its pooled total is at least the best single one's.
  Otherwise the best single one ships alone.

Five tries at once raise the chance that one passes by luck. With the
held-back check on top, a change with no real effect ships only a few
percent of the time.

## Descriptive only
MAE, rank correlation and the minutes Brier score by season. Nothing is
decided from these.
