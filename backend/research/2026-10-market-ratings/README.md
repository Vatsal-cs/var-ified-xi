# Team ratings from betting odds (October 2026) — not used

Pre-registered in `PREREGISTRATION.md` (commit 17b0702). Both sides rate past
seasons with the previous season's FPL ratings, as the live model must.

| Paired against lagged_ratings (5 seeds per season) | Pooled | 2024-25 | 2025-26 |
|---|---:|---:|---:|
| lagged_market_add: + team form from the goals the odds expected | +1 [−107, +111] | +4 | −3 |

No detectable effect, so it stays off (`config.TEAM_FORM_SOURCE = "xg"`, and
team form itself is off). The +107 that a season's own FPL ratings were worth
in 2025-26 isn't recovered by a recency-weighted market rating built during
the season; whatever those ratings carried (hindsight in the archived
snapshot, or a pre-season judgement of squads), it isn't this.

## Reproduce

```bash
research/2026-10-market-ratings/run.sh
python -m data_engine.evaluation research/2026-10-market-ratings/mkt_*.json --reference lagged_ratings
```
