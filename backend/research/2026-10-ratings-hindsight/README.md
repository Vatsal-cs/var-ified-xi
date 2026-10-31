# How much of the stale-ratings gap is hindsight — result

**Nearly all of it. Team-ratings work stops.** Pre-registered in
`PREREGISTRATION.md` (commit 7f62e4e) before any run.

FPL revises its team ratings during a season and the archive keeps only the
last version, so "production" rated every replayed match, GW1 included, with
end-of-season knowledge. `pit_ratings` rates each match with the version the
archive saved before its kickoff (17 versions for 2024-25, 12 for 2025-26):
what a live model would have had in a season when FPL publishes ratings.

| 5 seeds per season | 2024-25 | 2025-26 |
|---|---:|---:|
| lagged_ratings — last season's final ratings, as live in 2026-27 | 2435.2 | 2247.6 |
| pit_ratings — FPL's ratings as shown at each kickoff | 2362.0 | 2318.0 |
| production — the season's final file (hindsight) | 2515.8 | 2365.8 |

| Paired (`evaluation.txt`) | Pooled, 95% CI | 2024-25 | 2025-26 | Verdict |
|---|---:|---:|---:|---|
| **pit_ratings vs lagged_ratings (primary)** | **−3 [−131, +122]** | −73 | +70 | no detectable effect |
| production vs lagged_ratings | +199 [+56, +342] | +81 | +118 | the old "stale ratings cost ~100 a season" |
| production vs pit_ratings | +202 [+42, +367] | +154 | +48 | hindsight |

The gap between production and last season's ratings is the gap between
production and FPL's own live ratings: hindsight. FPL's live ratings did no
better than last season's final ones. They helped in 2025-26 (+70) and hurt
in 2024-25 (−73), and over the two seasons it comes to nothing.

So the live model isn't losing a measurable amount by rating teams with last
season's ratings. That is also why the four free replacements (xG form,
replaced and added; odds form, added and replaced) never beat them: there was
little real gap to close. The "−93 to −107 a season" quoted in
research/2026-10-stale-ratings and research/2026-10-lagged-team-form was
measured against hindsight.

## Side note for the harness (not decided here)

`production`, the reference for most research, rates replayed seasons with
end-of-season ratings, which flatters its totals by about 50-150 points a
season. A paired test is still fair when both sides share those ratings. A
test of anything that stands in for team quality is not, because it competes
with hindsight. Such tests should use `lagged_ratings` (how live works) or
`pit_ratings` as the reference.

## Reproduce

```bash
research/2026-10-ratings-hindsight/run.sh
python -m data_engine.evaluation research/2026-10-ratings-hindsight/rh_*.json --reference lagged_ratings
```
