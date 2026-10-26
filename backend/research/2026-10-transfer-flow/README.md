# Transfer flow as a model input (October 2026) — not used

Pre-registered in `PREREGISTRATION.md` (commit e571380): production plus
`transfer_flow`, the net transfers into a player before the deadline as a
percent of all that gameweek's transfers in.

| | 2024-25 | 2025-26 | Pooled |
|---|---:|---:|---:|
| Backtest, paired vs production (5 seeds) | −25 [−82, +26] | −22 [−81, +41] | **−47 [−127, +35]**, 3 of 10 runs ahead — no detectable effect, behind in both |

| | MAE | rank-r | Brier P(60+) |
|---|---|---|---|
| 2024-25 | 0.988 → 0.989 | 0.720 → 0.723 | 0.0868 → 0.0852 |
| 2025-26 | 0.909 → 0.909 | 0.752 → 0.755 | 0.0778 → 0.0757 |

The minutes model did get better at saying who plays 60+ in both seasons,
which is what step 1 pointed at (bought players out-started their
projections). It didn't turn into points: the squads scored less in 8 of 10
runs. Most of what the crowd's transfers know is apparently already in
ownership (shipped, +122) and the injury flags; what's left moves start
chances for fringe players more than it changes who's worth picking.

`config.TRANSFER_FLOW_FEATURE` stays False; the column is still built
(archive, this season's history and live rows) so the test can be re-run.

## Reproduce

```bash
research/2026-10-transfer-flow/run.sh
python -m data_engine.evaluation research/2026-10-transfer-flow/tf_*.json --reference production
```

`step1.py` reproduces the step-1 table in the pre-registration
(`step1_output.txt`).
