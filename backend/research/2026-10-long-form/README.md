# Long-run form (October 2026) — shipped

Pre-registered in `PREREGISTRATION.md` (commit 68c8331). Every other form
input looks back three to five gameweeks, so a good player in a cold month
read much like a poor one on a hot run. This adds points, minutes, xGI, BPS
and defensive contributions averaged over the last ten gameweeks
(`*_avg_10`) and over every earlier gameweek of the season
(`*_avg_season`). Both sides rate teams on the previous season's FPL
ratings, as the live model must in 2026-27.

| Tuning seasons, paired vs lagged_ratings (5 seeds) | 2024-25 | 2025-26 | Pooled |
|---|---:|---:|---:|
| lagged_long_form | +33 [−48, +107] | +69 [+27, +111] | **+102 [+9, +187]**, 8 of 10 runs — better |

| Held back, once | 2022-23 | 2023-24 | Pooled |
|---|---:|---:|---:|
| lagged_long_form | **+42** [−23, +107] | **+19** [−41, +77] | +60 [−28, +149], 7 of 10 runs — > 0 in both, shipped |

Accuracy barely moved: MAE within ±0.003 in every season, rank correlation
up 0.000–0.002, and the minutes model's Brier score a little better in all
four (e.g. 0.0778 → 0.0771 in 2025-26). The gain is in which players get
picked, not in the size of the projections. The pre-registered descriptive
check of the new inputs' share of the model's gain wasn't run: everything ran
on GitHub Actions to keep it off the laptop, and the artifacts don't keep
the fitted models.

`config.LONG_FORM_FEATURE = True`. Training rows average the gameweeks before
their own; prediction rows include the latest one, as the short windows do.

## Reproduce

Ran on GitHub Actions (`.github/workflows/backtest.yml`); the scripts are the
local equivalent. Since the inputs now ship, both variants match at HEAD, so
check out commit 3ef0b06 first.

```bash
research/2026-10-long-form/run.sh            # tuning seasons
research/2026-10-long-form/run_confirm.sh    # held-back seasons (once)
python -m data_engine.evaluation research/2026-10-long-form/lf_*.json --reference lagged_ratings
python -m data_engine.evaluation research/2026-10-long-form/conf_*.json --reference lagged_ratings
```
