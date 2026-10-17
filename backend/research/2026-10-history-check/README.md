# How much past-season data to train on, judged on 2026-27 itself (October 2026)

Pre-registered in `PREREGISTRATION.md`. 2026-27 replayed GW2-6, walk-forward,
live pipeline, only the training data changed. Squad points over GW2-6:

| Training data | seed 42 | seed 7 | seed 13 | seed 101 | seed 2024 | Mean | vs production | Seeds won |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 past seasons + this season (live) | 368 | 353 | 374 | 327 | 348 | 354.0 | +0.0 | — |
| 2025-26 + this season | 364 | 366 | 358 | 350 | 381 | 363.8 | +9.8 | 3/5 |
| 3 past seasons, older down-weighted | 376 | 358 | 382 | 366 | 330 | 362.4 | +8.4 | 4/5 |
| this season only | 301 | 271 | 295 | 287 | 284 | 287.6 | -66.4 | 0/5 |

Bar (written before the runs): beat production on at least 4 of 5 seeds AND
by 10+ points on average. **None clears it**, so the live training data stays.

- Dropping past seasons entirely is clearly worse: -66 over five gameweeks,
  every seed.
- Using less of them (the last season only, or older ones down-weighted)
  comes out about +9 over five gameweeks, close to the bar but under it: 3/5
  seeds for last-season-only, +8.4 for down-weighting. Down-weighting lost
  58 in the past-season backtests. Worth re-running when more of 2026-27 is
  played, before anything changes.

(First run note: last_season initially ignored its season list —
config.HISTORICAL_SEASONS is read at import — and matched production
exactly; fixed by passing the seasons explicitly and re-run.)

## Reproduce

```bash
python research/2026-10-history-check/replay.py <production|last_season|this_season|recency> <seed>
```
