# Team form from recent xG (October 2026) — stays off

FPL publishes no team strength ratings for 2026-27, so the live model uses last
season's (`historical_data.fallback_team_strengths`). Would a current-form
measure — each team's recency-weighted xG for and against, point-in-time
(`team_form.py`) — do better? Pre-registered in `PREREGISTRATION.md`.

| Test | FPL ratings | Team form | Paired difference |
|---|---:|---:|---:|
| Backtest 2024-25 (5 seeds) | 2389.8 | 2423.4 | +34 [−83, +154] |
| Backtest 2025-26 (5 seeds) | 2282.6 | 2130.0 | **−153 [−276, −24]** |
| Pooled | | | −119 [−292, +51] — not "better" |
| 2026-27 GW2-5 replay vs last season's ratings (3 seeds) | 292.3 | 267.0 | worse on every seed |

Not "better", so it stays off (`config.TEAM_FORM = False`). A few matches of xG
are noisier than a rating that reflects a whole season of squad quality. Worth
re-testing late in a season, or as a blend whose weight on form grows with
matches played.

Caveat recorded in advance: the archive holds one snapshot of FPL's ratings per
season, which may carry hindsight on the past-season side. The 2026-27 replay
has no such issue and points the same way.

## Reproduce

```bash
python -m data_engine.evaluation research/2026-10-team-form/tf_*.json --reference production
python research/2026-10-team-form/replay_2026.py    # needs the 9 Oct 2026 data cache
```
