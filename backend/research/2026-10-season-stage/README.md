# Season stage (matches_played) as a model input (October 2026) — not used

Pre-registered in `PREREGISTRATION.md` (commit f2ce959). Run in the cloud
(.github/workflows/backtest.yml, run 40415130060), 5 seeds per season.

| | 2024-25 | 2025-26 | Pooled |
|---|---:|---:|---:|
| Backtest, paired vs production | +34 [−9, +77] | −47 [−84, −9] | **−13 [−70, +44]**, 4 of 10 runs ahead — no detectable effect, split |

MAE 0.989 → 0.995 and 0.908 → 0.909; rank correlation and the minutes Brier
score unchanged. A split again, as on the pre-audit harness: telling the model
how far into the season it is doesn't fix the early over-projection after a
big game in a way that survives both seasons. matches_played stays out.

## Reproduce

Dispatch backtest.yml with variants "production season_stage", then
`python -m data_engine.evaluation research/2026-10-season-stage/backtest_*.json --reference production`.
