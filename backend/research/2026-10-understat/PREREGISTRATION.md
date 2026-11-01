# Understat shot data — pre-registration
Written 2026-11-01, before any run. Runs on GitHub Actions.

Why: FPL's per-match data stops at goals, assists, xG and xA. Understat
(free, no key) adds shot volume, key passes, non-penalty xG and xGChain /
xGBuildup, the expected goals of every possession a player was part of. That
shows build-up play and chance creation that never ends in an assist. Guessed
odds of helping: about 1 in 4 (set-piece duty looked as promising and lost).

## Data (understat_data.py)
Every league match of 2022-23 to 2025-26, fetched once and committed as
data/understat/{season}.json.gz. Players are linked to FPL inside their own
club: by name first, then for the rest by minutes matching FPL's in the same
matches. 99-100% of played FPL rows link in every season. Minutes agree within
5 on 90-97% of rows, and per-match npxG correlates 0.88 with FPL's xG (the
big gaps are penalties, which npxG leaves out). Played but unlinked rows are
skipped by the averages, not counted as zero.

## Variant (backtest.py "understat")
lagged_ratings plus ten inputs: shots, key passes, npxG, xGChain and
xGBuildup, each averaged over five gameweeks and the season so far
(config.UNDERSTAT_COLUMNS).

## Primary — backtest, points
understat vs lagged_ratings, seeds 42, 7, 13, 101, 2024; 2024-25 (trained on
itself) and 2025-26 (plus 2024-25); --bag-size 1.

- "Better" (pooled 95% CI above zero AND ahead in both seasons): ONE run on
  the held-back 2022-23 and 2023-24, logged in config's "Uses so far". It
  ships only if above zero in both. Shipping then needs the live side: this
  season's matches fetched in the weekly run, and FPL's live names linked the
  same way.
- Anything else: not shipped. The data and code stay, switched off.

## Descriptive only
MAE, rank correlation and the minutes Brier score by season.
