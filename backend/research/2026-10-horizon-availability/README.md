# Horizon-aware availability (step 3, October 2026)

Does valuing injured and suspended players' *later* weeks by FPL's return dates
and measured return curves — instead of production's flat tenth for the whole
horizon — make better transfer decisions?

**Verdict: no detectable effect. Stays off** (`config.HORIZON_AVAILABILITY = False`),
per the rule written before the runs (`PREREGISTRATION.md`).

| Test | 2024-25 | 2025-26 | Pooled, 95% CI |
|---|---:|---:|---:|
| Paired branch test (primary) | +5 | 0 | +4.7 [−26, +33] |
| Full-season simulation (safety check) | −8 | 0 | −8 [−69, +41] |

The rule changed **11 of 222** weekly decisions (6 runs × 37 gameweeks), all in
2024-25, each worth between −13 and +25 points. In 2025-26 it changed none.
It does change projections — 49–61 players a week — but almost never for a
player the planner is deciding about: an injured player you own scores nothing
next week under either rule, so he's benched or sold either way.

## Reproduce

```bash
D=research/2026-10-horizon-availability

# primary: the paired branch test
python -m data_engine.evaluation $D/e4_*.json --reference branch:production \
       --variants branch:production_e4 --block 6

# safety check: the full-season simulation
python -m data_engine.evaluation $D/e4_*.json --reference production \
       --variants production_e4 --block 4
```
