# Ownership as a model input (October 2026) — shipped

Found in the GW7 2026-27 audit: `selected_by_percent` was in FEATURE_COLUMNS
but 0 in every training row (the archive keeps ownership as `ownership`, and
this season's rows never carried FPL's per-gameweek `selected`), so neither
model ever split on it, while live rows held real percentages. Pre-registered
in `PREREGISTRATION.md` (commit e00626d).

| | 2024-25 | 2025-26 | Pooled |
|---|---:|---:|---:|
| Tuning seasons, paired vs production (5 seeds) | +59 [−11, +127] | +63 [−0, +130] | **+122 [+26, +216]**, 8 of 10 runs — better |

| Held back, once | 2022-23 | 2023-24 | |
|---|---:|---:|---:|
| Paired vs production (5 seeds) | **+65** | **+14** | > 0 in both — shipped |

Accuracy moved the same way in all four seasons: MAE 0.996→0.988,
0.912→0.909, 1.124→1.105, 0.964→0.958; the minutes model's Brier score fell
in each (e.g. 0.0887→0.0868). Ownership is the crowd's read of who's good and
who's starting, which the model had no other way to see.

`config.OWNERSHIP_FEATURE = True`: training rows get the share of managers
owning the player that gameweek, in percent (archive: selections / (total /
15); this season: the same from FPL's per-gameweek `selected`); live rows use
FPL's `selected_by_percent`.

## Reproduce

```bash
research/2026-10-ownership/run.sh            # tuning seasons
research/2026-10-ownership/run_confirm.sh    # held-back seasons (once)
python -m data_engine.evaluation research/2026-10-ownership/own_*.json --reference production
python -m data_engine.evaluation research/2026-10-ownership/conf_*.json --reference production
```
