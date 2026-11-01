# Five model changes (November 2026) — none used

Pre-registered together in `PREREGISTRATION.md` (commit 46669ab). Each
change was tested alone against lagged_ratings, the model as it runs live
(long-run form on, last season's team ratings). 5 seeds per season, run on
GitHub Actions.

| Paired vs lagged_ratings | Pooled | 2024-25 | 2025-26 | Verdict |
|---|---:|---:|---:|---|
| form_trend: last three gameweeks minus the season level | −75 [−161, +11] | −44 | −30 | no detectable effect, behind in both |
| per90: season-so-far rates per 90 minutes | −61 [−130, +14] | −36 | −25 | no detectable effect, behind in both |
| long_form_rest: 10-gameweek/season windows for starts, xG, xA, CS, saves, xGC | −66 [−157, +27] | −7 | −58 | no detectable effect, behind in both |
| last_season: previous season's minutes and per-90 record | **−147** [−237, −56] | −80 | −67 | ❌ worse |
| deeper_trees: depth 6 instead of 4 | **−145** [−252, −39] | −34 | −111 | ❌ worse |

Nothing reached the held-back seasons. Accuracy barely moved (MAE within
±0.01, rank correlation within ±0.003), so these are differences in which
players get picked, not in how well points are predicted. Long-run form
already gives the model a player's level. Breakout and per-90 versions of
the same averages only add near-duplicate inputs, and last season's record
overlaps with price and ownership. Deeper trees fit more noise.

All six variants, Understat's included (research/2026-10-understat), came in
below the reference. Part of that may be the reference itself: it is the
long-run form model, picked because it won, and its 2025-26 total (2297) sits
near the top of its seed range. Later changes are measured against a lucky
draw. The paired test still says none of them helps.

## Reproduce

```bash
gh workflow run backtest.yml -f seasons="2024-25 2025-26" \
  -f variants="lagged_ratings form_trend per90 long_form_rest last_season deeper_trees" \
  -f seeds="42 7 13 101 2024" -f reference=lagged_ratings -f extra_args="--bag-size 1"
python -m data_engine.evaluation research/2026-10-model-batch/mb_*.json --reference lagged_ratings
```
