# Bookings (November 2026) — no detectable effect, not used

Pre-registered in `PREREGISTRATION.md` (commit ac5d390): does telling the
model who gets booked (yellow cards over ten gameweeks and the season, red
cards over the season) score more points? Asked after GW10, when Thiago was
sent off after 22 minutes. Paired against lagged_ratings, 5 seeds a season,
run on GitHub Actions.

| | 2024-25 | 2025-26 | Pooled | Runs won | Verdict |
|---|---:|---:|---:|---:|---|
| bookings vs lagged_ratings | +4 [−57, +60] | −35 [−95, +24] | −31 [−116, +52] | 4 / 10 | no detectable effect — not used |

MAE, rank correlation and the minutes Brier score barely moved (2025-26 MAE
0.912 → 0.910). A yellow is −1, and the model already learns the average
card cost from the scores it trains on; which players get booked is too
small a difference to change who it picks. Thiago's red wasn't predictable
from his record either (four yellows, no reds before it).

The inputs stay built (config.BOOKINGS_COLUMNS) but are not model inputs.
Bans are handled separately: FPL flags a suspended player with his return
date, and the plan treats that like an injury.

## Reproduce

```bash
# cloud: .github/workflows/backtest.yml, seasons "2024-25 2025-26",
# variants "lagged_ratings bookings", reference lagged_ratings,
# seeds "42 7 13 101 2024", extra_args "--bag-size 1"
python -m data_engine.evaluation research/2026-11-bookings/bk_*.json --reference lagged_ratings
```
