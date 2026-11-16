# Chip timing (November 2026) — no detectable effect, the planner stays

Pre-registered in `PREREGISTRATION.md` (commit a1211d4), before any code or
run. The season simulator now scores Bench Boost, Triple Captain and Free Hit
on production's own squads (`season_sim --chips`, `data_engine/chip_sim.py`)
and races when to play them. Run on GitHub Actions (simulate.yml, run
43727062325), 5 seeds a season, `--bag-size 1`.

| Paired vs fixture_rule (5 seeds) | Pooled | 2024-25 | 2025-26 | Runs won | Verdict |
|---|---:|---:|---:|---:|---|
| planner (production) | −26 [−103, +44] | −18 [−70, +29] | −8 [−69, +42] | 1 / 10 | no detectable effect |
| hindsight (descriptive) | +175 [+48, +311] | +102 | +73 | 10 / 10 | upper bound |

No detectable effect, so by the rule written first the planner stays. It was
behind in both seasons and 9 of 10 runs, but by less than the test can tell
from noise.

## What chips are worth
Points a season over playing none, mean of 5 seeds:

| | 2024-25 | 2025-26 |
|---|---:|---:|
| fixture_rule | +64 | +64 |
| planner | +46 | +56 |
| hindsight | +167 | +137 |

So the simulator's no-chip totals sit about 50–65 points a season below a
manager who plays them sensibly, and two thirds of what's on the table can't
be reached without knowing the scores.

## Where the difference comes from
Average realised points per play (10 plays each):

| Chip, half | planner | fixture_rule | hindsight | planner's week = rule's |
|---|---:|---:|---:|---:|
| Triple Captain, 1st | 9.5 | 9.0 | 19.1 | 3 / 10 |
| Bench Boost, 1st | 6.5 | 4.5 | 20.1 | 0 / 10 |
| Free Hit, 1st | −1.8 | 1.2 | 36.3 | 3 / 10 |
| Triple Captain, 2nd | 16.7 | 17.1 | 20.2 | 4 / 10 |
| Bench Boost, 2nd | 9.0 | 8.4 | 22.2 | 0 / 10 |
| Free Hit, 2nd | 11.3 | 24.1 | 33.9 | 1 / 10 |

- **Nearly all of the gap is the second-half Free Hit.** The rule plays it in
  the biggest blank gameweek (+24); the planner mostly chose a double
  gameweek (GW33 in 6 of 10 runs, +11). In a blank, the Free Hit replaces
  players who have no match at all; in a double, the squad you own is
  already having a good week.
- **A first-half Free Hit was worth about nothing** under either policy (−1.8
  and +1.2). Neither season had a real blank before GW19. The planner's
  projected Free Hit gains in ordinary weeks didn't happen: a squad picked as
  the best of ~600 noisy projections looks better on paper than it is (the
  optimizer's curse), and the squad it replaces was picked by the same
  projections. Descriptive only.
- Triple Captain and Bench Boost came out about even. Bench Boost is small
  under both (4–9 points); most of its hindsight value is luck.
- The planner never lost a chip to its deadline. A bug that would have let it
  (no chips placed when fewer weeks were left than chips held) was found
  while building this test and fixed before any run (commit c5f9341).

## Limits
As pre-registered, plus one found after the runs: the simulator's
projections for weeks after the first read the cup, European and
international inputs from those weeks' archived rows, so they know who
started midweek games and internationals that hadn't been played yet. That
can only flatter the planner, which uses those weeks; the fixture rule
doesn't. It didn't change the verdict.

## What it suggests (not decided here)
A Free Hit saved for the biggest blank gameweek, with the planner timing the
other chips. That's a new rule, picked after seeing these numbers, so it
needs its own pre-registration and the held-back seasons before it could
change anything live.

## Reproduce

```bash
gh workflow run simulate.yml -f seasons="2024-25 2025-26" -f policies="production" \
  -f seeds="42 7 13 101 2024" -f extra_args="--chips --bag-size 1"
python -m data_engine.evaluation research/2026-11-chips/chips_*.json \
       --reference production+fixture_rule_chips --block 4
```
