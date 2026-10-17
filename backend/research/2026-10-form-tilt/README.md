# Early-season tilt toward points per match played (October 2026) — not used

Pre-registered in `PREREGISTRATION.md` (commit 75b53ea). For gameweeks 1-10,
projections pulled toward each player's points per match played over his last
five (weight fitted on the other season: 0.10 / 0.17).

| | 2024-25 | 2025-26 | Pooled |
|---|---:|---:|---:|
| production (5 seeds) | 2456.8 | 2302.6 | |
| form_tilt (5 seeds) | 2445.8 | 2296.0 | |
| Paired difference | −11 [−27, +2] | −7 [−29, +16] | **−17.6 [−45, +9]**, 3 of 10 cells won |

Behind in both seasons: not used. The squared-error fit said recent points
deserved a little more weight early on; picking squads on it lost points
instead. Players on a scoring run were already priced into the projection as
much as the points say they should be — the extra weight bought the run, not
what followed it.

## Reproduce

```bash
research/2026-10-form-tilt/run.sh
python -m data_engine.evaluation research/2026-10-form-tilt/ft_*.json --reference production
```
