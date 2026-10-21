# Stale FPL ratings replaced by odds-based ratings (October 2026) — not used

Pre-registered in `PREREGISTRATION.md` (commit 0707500). Both sides rate past
seasons with the previous season's FPL ratings, as live; 5 seeds per season.

| Paired vs lagged_ratings | 2024-25 | 2025-26 | Pooled | Runs won |
|---|---:|---:|---:|---:|
| lagged_market_replace | +14 | −42 | −28 [−128, +75] | 5 / 10 |

No detectable effect, behind in 2025-26: the stale ratings stay. With the
xG-form (replace and add) and odds-form (add) tests, every free replacement
for this season's missing ratings has now failed to beat last season's.

    research/2026-10-market-replace/run.sh
    python -m data_engine.evaluation research/2026-10-market-replace/mr_*.json --reference lagged_ratings
