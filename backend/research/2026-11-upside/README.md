# Upside mode (November 2026) — closed

Pre-registered in `PREREGISTRATION.md` (commit b53f571), with a declared
addendum (commit c435f06). The question: does picking on a player's
80th-percentile "good day" instead of his mean buy more huge seasons, the
kind a top-10 world finish needs? "Huge" means the reference model's own top
1% of seasons, rebuilt from weekly scores (`tail.py`).

| Tuning seasons (5 seeds) | Huge-season chance 2024-25 / 2025-26 | Average vs lagged_ratings |
|---|---:|---:|
| lagged_ratings (reference) | 1.00% / 1.03% | — |
| upside_captain: armband on the good day | 0.81% / 1.43% | −11 [−65, +37] |
| upside_half: picks halfway to the good day | 1.26% / 0.10% | −43 [−142, +66] |
| upside_full: picks and armband on the good day | 1.80% / 2.56% | +49 [−89, +204] |

None passed (needed 2.0% in both seasons). upside_full came close and cost
nothing on average, so it got one declared look at the held-back seasons:

| Held back (5 seeds) | Huge-season chance 2022-23 / 2023-24 | Average |
|---|---:|---:|
| upside_full | **0.31% / 0.21%** (reference 1%) | **−61 and −72**, −132 [−296, +31], 0 of 10 runs ahead |

Closed. On new seasons, chasing upside gave fewer big seasons, not more, and
cost points. The good-day model's picks are noisier rather than bolder: the
spread it adds is mostly bad weeks. The tuning-season near miss was noise,
as the uneven pattern (half worse than both captain-only and full) already
hinted. The model stays on the mean projection.

## Reproduce

```bash
gh workflow run backtest.yml -f seasons="2024-25 2025-26" \
  -f variants="lagged_ratings upside_captain upside_half upside_full" \
  -f seeds="42 7 13 101 2024" -f reference=lagged_ratings -f extra_args="--bag-size 1"
gh workflow run backtest.yml -f seasons="2022-23 2023-24" -f variants="lagged_ratings upside_full" \
  -f seeds="42 7 13 101 2024" -f reference=lagged_ratings -f extra_args="--bag-size 1"
python research/2026-11-upside/tail.py research/2026-11-upside/up_*.json
python research/2026-11-upside/tail.py research/2026-11-upside/conf_*.json
```
