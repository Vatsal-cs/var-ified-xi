# Understat shot data (November 2026) — not used

Pre-registered in `PREREGISTRATION.md` (commit 6eb6a40). Shots, key passes,
non-penalty xG, xGChain and xGBuildup for every league match 2022-23 to
2025-26, linked to 99-100% of played FPL rows (by name in the club, then by
matching minutes). Averaged over five gameweeks and the season so far.

| Paired vs lagged_ratings (5 seeds) | Pooled | 2024-25 | 2025-26 |
|---|---:|---:|---:|
| understat | **−111** [−198, −27], 2 of 10 runs ahead | −14 [−76, +43] | −97 [−161, −35] |

Worse, so it never reached the held-back seasons. Accuracy didn't move (MAE
0.994 → 0.993 and 0.912 → 0.911). FPL's own per-match xG, xA, ICT and BPS
already describe shot volume and build-up closely enough. Ten more inputs
that say nearly the same thing just give the trees more ways to split on
noise. `config.UNDERSTAT` stays off. The packs (data/understat) and
understat_data.py stay, so it can be re-run.

## Reproduce

```bash
gh workflow run backtest.yml -f seasons="2024-25 2025-26" -f variants="lagged_ratings understat" \
  -f seeds="42 7 13 101 2024" -f reference=lagged_ratings -f extra_args="--bag-size 1"
python -m data_engine.evaluation research/2026-10-understat/us_*.json --reference lagged_ratings
```
