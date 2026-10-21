# Club rotation rate, and calibrated points-if-60+ (October 2026) — neither used

Pre-registered in `PREREGISTRATION.md` (commit 0707500); production includes
ownership (shipped before any run). 5 seeds per season, paired vs production.

| Variant | 2024-25 | 2025-26 | Pooled | Runs won | Verdict |
|---|---:|---:|---:|---:|---|
| team_rotation (starters changed per match, club's last five) | +12 | −31 | −19 [−80, +43] | 6 / 10 | no detectable effect — not used |
| calibrated (points-if-60+ through the real-average curve) | +6 | −35 | −29 [−123, +69] | 4 / 10 | no detectable effect — not used |

Both behind in 2025-26. The rotation rate made the minutes model jumpier
about every player at a club that rotates; calibration pulled the premiums
down, and squads built on it scored less — the top-end over-projection
doesn't cost points because squads are chosen on order, which it barely
changes (as the earlier linear shrink found).

    research/2026-10-rotation-calibration/run.sh
    python -m data_engine.evaluation research/2026-10-rotation-calibration/rc_*.json --reference production
