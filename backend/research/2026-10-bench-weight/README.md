# Bench weight (October 2026) — stays at 0.12

Prompted by the live team carrying ~£22m and ~18 points a week on its bench:
does counting bench players for less move money into the XI and score more?
Pre-registered in `PREREGISTRATION.md`.

| Test | 6% | 3% | 1% |
|---|---:|---:|---:|
| Backtest, squads from identical predictions (5 seeds × 2 seasons) | +16.6 [−9, +45] | +25.2 [−10, +62] | +15.4 [−27, +56] |
| Simulator, paired branch test (3 seeds × 2 seasons) | — | −36.3 [−85, +11] | — |
| Simulator, full season | — | +13.0 [−91, +112] | — |

No weight is "better" in the backtest, so by the pre-registered rule nothing
ships. In the transfer-constrained simulator the 3% weight changed 32 of 216
weekly decisions and did slightly worse on them.

What actually built the expensive bench: the squad builder (used for the
team's GW2 creation) rewards every squad member at 30% of his six-week value
whether he starts or not, and one free transfer a week can't undo that. A
Wildcard planned by the transfer planner (`backend/wildcard.py`) produces a
lean bench (~£18m) at the existing 0.12.

## Reproduce

```bash
D=research/2026-10-bench-weight
python -m data_engine.evaluation $D/bt_*.json --reference production
python -m data_engine.evaluation $D/sim_*.json --reference branch:production \
       --variants branch:production_bench0.03 --block 6
```
