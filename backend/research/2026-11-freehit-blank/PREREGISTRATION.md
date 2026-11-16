# Free Hit saved for the blank — pre-registration
Written 2026-11-15, before any code or run.

Why: in the chip timing test (research/2026-11-chips) nearly all of the
planner's gap to the save-them-for-blanks-and-doubles habit was the
second-half Free Hit: +24 a play in the biggest blank gameweek, +11 where the
planner put it, mostly a double. Triple Captain and Bench Boost came out about
even. So the candidate is a hybrid: the Free Hit goes to the biggest blank,
and the planner times the rest.

That idea was picked after seeing 2024-25 and 2025-26, so those seasons can't
test it. The decision is made on the held-back seasons, 2022-23 and 2023-24,
which no chip question has been run on.

## Policies (`season_sim --chips`, as in the chip timing test)
- **planner** (production, the reference): unchanged. Each week,
  `chip_planner.plan` with the chips still held and projections out to the
  half's deadline.
- **hybrid** (candidate): in a half with at least one blank gameweek from GW3
  on, the Free Hit is fixed to the week the fixture rule picks for it: most
  blank clubs, ties to the earlier week. The planner times Triple Captain and
  Bench Boost as now, without the Free Hit and without that week. In a half
  with no blank, the hybrid is the planner.

Scoring, chip rules and squads are exactly as in the chip timing test: one of
each chip per half, the first half's by GW19, chips from GW3, the Wildcard not
modelled, each chip's realised gain added to production's week.

From the fixture calendars, the hybrid's Free Hit weeks are fixed now:

| | 1st half | 2nd half |
|---|---|---|
| 2022-23 | GW8 (6 clubs blank) | GW28 (6) |
| 2023-24 | GW17 (2) | GW29 (12) |
| 2024-25 | GW15 (2) | GW29 (4) |
| 2025-26 | planner (no blank) | GW34 (6) |

## Primary
hybrid vs planner on realised points per gameweek, 2022-23 (trained on
itself) and 2023-24 (plus 2022-23), seeds 42, 7, 13, 101, 2024,
`--bag-size 1`, run ONCE. Standard verdicts (`evaluation.py`, block 4):

- **better** (pooled 95% CI above zero AND ahead in both seasons): live, the
  Free Hit is held for the biggest blank of each half (below).
- **no detectable effect** or **worse**: the planner stays as it is.

## Descriptive only
The same comparison on 2024-25 and 2025-26: where the idea came from, so it
can only show the code does what the rule says, not that the rule works. Per
chip and half, average realised gain under each policy; how often the planner
already chose the hybrid's Free Hit week. Nothing is decided from these.

## If it ships, live
The planner gets the Free Hit only in a half with no blank. Live, a blank is
known only once it's announced, so the Free Hit is held while one is
scheduled or could still be. If none is by the half's deadline week, the
planner places it among the weeks left.

## Limits, stated now
- The simulator reads the whole fixture calendar, so it knows every blank
  from the start of a half. Live, second-half blanks are announced weeks
  ahead. Holding the Free Hit costs little if ordinary-week Free Hits are
  worth about nothing, as they were in the chip timing test, but that is
  where the two differ.
- The simulator's projections for weeks after the first read the cup,
  European and international inputs from those weeks' archived rows (found
  after the chip timing test, left as it was so the two tests compare). It
  sharpens the planner's view of later weeks, so it can only favour the
  reference.
- The two policies differ only where the Free Hit goes (and what that frees
  for the other two chips): two decisions per season-seed, ten per season.
  2023-24's second half has a 12-club blank, which the planner may pick
  itself; then the two agree there. "No detectable effect" is a likely result
  and would mean the test can't tell.
- Everything else stated in the chip timing test's limits applies.
