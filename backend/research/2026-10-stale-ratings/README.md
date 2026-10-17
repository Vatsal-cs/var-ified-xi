# Training on stale team ratings (October 2026) — not used

Pre-registered in `PREREGISTRATION.md` (commit de0b3f7). 2025-26 replayed with
2024-25 as the prior season, 5 seeds.

| | 2025-26 points (5 seeds) | Paired vs live_ratings |
|---|---:|---:|
| live_ratings — the live set-up: trained on own ratings, played on last season's | 2209.6 | — |
| lagged_ratings — trained on stale ratings too | 2195.2 | −14 [−85, +58] |

No detectable effect, so live training keeps each past season's own ratings.
The suspicion was that the model trusts last season's ratings as much as it
learned to trust fresh ones; teaching it on stale ratings doesn't win points,
so that trust isn't what costs them.

What stale ratings DO cost: production (fresh ratings for training and replay)
scored 2302.6 on the same seeds (research/2026-10-lagged-team-form), so playing
on last season's ratings is worth about −93 points a season. Nothing free tried
so far recovers it (xG form replaced or added, odds-based form added); some of
it may be hindsight in the archived ratings that no live model could have.

## Reproduce

```bash
research/2026-10-stale-ratings/run.sh
python -m data_engine.evaluation research/2026-10-stale-ratings/sr_25_s*.json --reference live_ratings
```
