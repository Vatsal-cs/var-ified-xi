# Planner horizon decay 0.95 (October 2026) — not adopted

Pre-registered in `PREREGISTRATION.md` (commit ec79f7a). Paired branch test
in the simulator, GW2-38, 3 seeds per season, cloud (simulate.yml, run
40411764990). Each decision is scored over the next six gameweeks from the
same position, so the totals add overlapping six-week windows.

| | 2024-25 | 2025-26 | Pooled |
|---|---:|---:|---:|
| production_decay95 − production | +110 [−9, +251] | −49 [−180, +43] | **+60 [−109, +239]**, won 4 of 6 — no detectable effect, split |

Valuing later weeks more helped in 2024-25 and hurt in 2025-26.
HORIZON_DECAY stays 0.85, now as a tested setting rather than an argued one.
The `horizon_decay` knob stays on the planner for re-testing.

## Reproduce

```bash
python -m data_engine.evaluation research/2026-10-horizon-decay/sim_*.json \
       --reference branch:production --variants branch:production_decay95 --block 4
```
