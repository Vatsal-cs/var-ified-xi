# Choosing the XI after autosubs (October 2026) — worse, not used

Pre-registered in `PREREGISTRATION.md` (commit a03050c): from the squad as
decided, field the XI and bench order with the most expected points AFTER
autosubs (data_engine/lineup.py), instead of the XI with the most expected
points. Same squads, same decisions otherwise, so every week is paired.

| | 2024-25 | 2025-26 | Pooled |
|---|---:|---:|---:|
| Simulator, production@lineup vs production (3 seeds, cloud) | −13 [−38, +8] | −24 [−52, +1] | **−37 [−75, −4]**, 0 of 6 runs ahead — **worse** |
| Backtest (5 seeds, secondary) | +3 [−8, +17] | −18 [−31, −7] | −14 [−31, +3] |

The idea is right in principle and loses in practice. It changes few weeks,
and the players it starts over the expected-points choice almost always play
(2025-26 backtest: 1 of its 55 swaps didn't, against 5 of the players it
benched) and score less (175 vs 201). Its edge rests on points-if-he-plays
= xP / P(plays), which runs high for the less certain starters it promotes.
Expected points already prices the rotation risk about right.

Production keeps choosing the XI on expected points. `lineup.py` and the
`--lineup` flag on both harnesses stay for re-testing.

## Reproduce

```bash
# cloud: .github/workflows/simulate.yml, seasons "2024-25 2025-26", policies
# production, seeds "42 7 13", extra_args "--lineup --bag-size 1"
python -m data_engine.evaluation research/2026-10-lineup/sim_*.json --reference production --block 4
research/2026-10-lineup/run_backtest.sh
python -m data_engine.evaluation research/2026-10-lineup/bt_*.json --reference production
```
