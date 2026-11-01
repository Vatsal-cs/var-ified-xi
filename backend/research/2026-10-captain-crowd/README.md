# The crowd's captain (November 2026) — not used

Pre-registered in `PREREGISTRATION.md` (commit f5a7d6e). Same squad and XI
as the model. The armband goes to the XI's most-owned player within 1 point
of its best projection.

| Paired vs lagged_ratings (5 seeds) | Pooled | 2024-25 | 2025-26 |
|---|---:|---:|---:|
| captain_crowd | +11 [−23, +44], 5 of 10 runs ahead | +20 [−6, +48] | −10 [−32, +11] |

No detectable effect. The armband changed hands in 88 of 370 gameweeks (24%)
and the points came out even. The crowd's captain carries nothing the
model's mean projection lacks: ownership is already one of its inputs. The
Canada top 20's Haaland gain in 2026-27 is one season's outcome, not a rule
that wins across seasons. The model keeps captaining on its own projection.

## Reproduce

```bash
gh workflow run backtest.yml -f seasons="2024-25 2025-26" -f variants="lagged_ratings captain_crowd" \
  -f seeds="42 7 13 101 2024" -f reference=lagged_ratings -f extra_args="--bag-size 1"
python -m data_engine.evaluation research/2026-10-captain-crowd/cc_*.json --reference lagged_ratings
```
