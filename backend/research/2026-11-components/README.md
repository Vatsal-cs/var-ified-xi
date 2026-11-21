# Points by part (November 2026) — not used

Pre-registered in `PREREGISTRATION.md` (commit 57e84ca) before any run.
Stage 2 predicted goals, assists, clean sheet, bonus and the rest
separately and added them up with FPL's scoring, instead of one regressor
on total points.

| Paired vs lagged_ratings (5 seeds) | Pooled | 2024-25 | 2025-26 | Runs ahead |
|---|---:|---:|---:|---:|
| points_by_part | −22 [−149, +103] | +10 [−91, +101] | −32 [−111, +54] | 5 of 10 |

**No detectable effect, so it stays off** (`config.POINTS_BY_PART = False`).
- Accuracy improved in 2024-25 (MAE 0.994 → 0.968) and was level in
  2025-26 (0.912 → 0.910).
- Rank correlation and the start-chance score were unchanged.
- As in earlier studies, better accuracy did not turn into more points. The
  total-points regressor already learns the position scoring from
  element_type and the form inputs, so splitting it up mostly adds variance
  in which players come out on top.

Same run as `research/2026-11-haul-dampen` (shared reference). The files
are `backtest_*.json`, and the table is in `evaluation.txt`.

## Reproduce

```bash
gh workflow run backtest.yml --ref audit/model-2026-11 -f seasons="2024-25 2025-26" \
  -f variants="lagged_ratings points_by_part haul_dampen" -f seeds="42 7 13 101 2024" \
  -f reference=lagged_ratings -f extra_args="--bag-size 1"
python -m data_engine.evaluation research/2026-11-components/backtest_*.json --reference lagged_ratings --block 4
```
