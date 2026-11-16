# Free Hit saved for the blank (November 2026) — no detectable effect, the planner stays

Pre-registered in `PREREGISTRATION.md` (commit 09ad754), before any code or
run. The idea came out of the chip timing test (research/2026-11-chips):
there, a second-half Free Hit in the biggest blank gameweek averaged +24 to
the planner's +11. So the hybrid plays the Free Hit in each half's biggest
blank and lets the chip planner time Triple Captain and Bench Boost around it.
It was decided ONCE on the held-back 2022-23 and 2023-24, which no chip
question had been run on. Season simulator, GitHub Actions (simulate.yml, runs
43787483325 and 43787492728), 5 seeds a season, `--bag-size 1`, code at
commit 36d7e63.

| Hybrid vs planner (5 seeds) | Pooled | Season 1 | Season 2 | Runs won | Verdict |
|---|---:|---:|---:|---:|---|
| **2022-23, 2023-24 (held back, decides)** | **−3 [−98, +75]** | +21 [−26, +69] | −24 [−104, +37] | 5 / 10 | **no detectable effect** |
| 2024-25, 2025-26 (where the idea came from) | +29 [−22, +93] | +12 [−27, +61] | +17 [−10, +60] | 8 / 10 | descriptive only |

No detectable effect on the held-back seasons, so by the rule written first
the planner stays as it is.

## What happened
The pattern that suggested the hybrid didn't come back. Average realised
points per Free Hit, 10 plays each:

| Free Hit | Held back: planner | Held back: hybrid | Tuning: planner | Tuning: hybrid |
|---|---:|---:|---:|---:|
| 1st half | −1.1 | 13.1 | −1.8 | −1.2 |
| 2nd half | 27.6 | 12.1 | 11.3 | 24.1 |

- **The second half reversed.** On the tuning seasons the blank beat the
  planner's choice by 13 a play; on the held-back seasons the planner's
  choice beat the blank by 15. The planner mostly played it in the
  season's late double gameweeks (GW37 in 7 of 10 runs), and it never chose
  the same week as the hybrid.
- **2023-24's 12-club blank (GW29) was worth only +11** to the Free Hit. With
  only 8 clubs playing, a Free Hit has few players to pick from, and the
  simulated squad had probably already moved towards players with a match
  (not measured). A big blank isn't automatically a big Free Hit.
- **The first half went the hybrid's way** in both held-back seasons: +15 a
  play to the planner's −12 in 2022-23 (GW8, 6 clubs out), +11 to +10 in
  2023-24 (GW17, 2 clubs out). Pooled, the planner's first-half Free Hit was
  again worth about nothing (−1.1 held back, −1.8 tuning), as in the chip
  timing test. A first-half-only rule would be picked after seeing these
  numbers, so nothing is decided on it here.
- Triple Captain and Bench Boost came out about level between the two (the
  planner timed them in both), and no chip was left unplayed.

## What it means
The chip timing test's lesson was "the second-half Free Hit belongs in the
blank". Two more seasons say that was those two seasons. Where the Free Hit
does best depends on how big the blank is against how good the doubles are,
and on how ready the squad already is for both. That is the trade the
planner prices each week, and nothing here beats it.

## Limits
As pre-registered. The simulator's later-week projections still read cup,
European and international inputs from archived rows, which can only favour
the planner (the reference). The simulator also knows every blank and double
from the start of a half.

## Reproduce

```bash
gh workflow run simulate.yml -f seasons="2022-23 2023-24" -f policies="production" \
  -f seeds="42 7 13 101 2024" -f extra_args="--chips --bag-size 1"
python -m data_engine.evaluation research/2026-11-freehit-blank/freehit_2[23]_*.json \
       --reference production+planner_chips --block 4
```

The tuning seasons: `seasons="2024-25 2025-26"`, files `freehit_2[45]_*.json`.
