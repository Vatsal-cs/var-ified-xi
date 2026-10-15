# This season's team form, with last season's ratings (October 2026) — not used

The two earlier team-form tests replayed past seasons with that season's own
FPL ratings, which the live model doesn't have (it uses the season before's).
This one runs both sides the way live works. Pre-registered in
`PREREGISTRATION.md` (commit 5a23856).

| Paired against lagged_ratings (5 seeds per season) | Pooled | 2024-25 | 2025-26 |
|---|---:|---:|---:|
| lagged_team_form_add (primary) | +6 [−118, +123] | +13 | −7 |
| production, the season's own ratings (descriptive) | +128 [−18, +269] | +20 | **+107 [+17, +198]** |

Primary: no detectable effect, so team form stays off live.

Descriptive: team ratings matter. Rating 2025-26 with its own FPL ratings
instead of 2024-25's was worth about +107 points that season (+20 in 2024-25).
Whether that is hindsight in the archived snapshot or simply better ratings,
it is the largest gap any input has shown, and the place to look next for a
current-season rating that isn't xG form (which has now failed three ways).

## Reproduce

```bash
research/2026-10-lagged-team-form/run.sh
python -m data_engine.evaluation research/2026-10-lagged-team-form/ltf_*.json --reference lagged_ratings
```
