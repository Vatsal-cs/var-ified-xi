# Chip timing — pre-registration
Written 2026-11-15, before any code or run.

Why: neither harness plays chips, so the chip planner (`chip_planner.py`),
which decides live when to play Triple Captain, Bench Boost and Free Hit, has
never been judged on realised points. After GW8 the top-10k sample had 17
chip points to the live team's 0 (research/2026-10-top-gap). This is about
timing only: given the same squads, does the planner put the chips in better
weeks than the habit most managers follow?

## What the simulator does (`season_sim --chips`)
The production policy plays the season exactly as now. Bench Boost, Triple
Captain and Free Hit never change the squad carried into the next week, so
each chip's realised gain in every week can be scored on the same season:

- **Bench Boost**: the whole squad's points with no autosubs, minus the
  week's real score.
- **Triple Captain**: one more copy of the armband's points (the vice's if the
  captain didn't play), as FPL scores it.
- **Free Hit**: the best one-week squad the model can buy that week
  (`chip_planner.free_hit_squads`, budget = selling value + bank), scored with
  autosubs and the armband on its top two projections, minus the week's real
  score.

Chip rules as in 2025-26 and 2026-27, for both seasons: one of each per half,
the first half's played by GW19, the second's by the season's last gameweek.
Chips are played from GW3 (GW2 builds the opening squad). The Wildcard isn't
modelled: it changes the squad, which this design holds fixed.

## Policies
- **planner** (production): each week, `chip_planner.plan` with the chips
  still held, projections out to the half's deadline from that week's model,
  and the squad as it stands held for later weeks. A chip placed in the
  current week is played.
- **fixture_rule** (reference): the common habit of saving chips for blank and
  double gameweeks, fixed per half from the fixture calendar. Free Hit in the
  week with the most blank teams; Bench Boost in the week with the most
  doubling teams; Triple Captain in the next-biggest double week. A chip with
  no such week goes to the half's last free weeks: Triple Captain the
  deadline week, then Bench Boost, then Free Hit. Ties go to the earlier week.
- **hindsight** (descriptive only): each half's best placement on realised
  gains. An upper bound no policy can reach.

## Primary
planner vs fixture_rule on realised points per gameweek (production's score
plus chip gains). Seeds 42, 7, 13, 101, 2024; 2024-25 (trained on itself) and
2025-26 (plus 2024-25), as `simulate.yml` runs them; `--bag-size 1`. Standard
verdicts (`evaluation.py`, block 4):

- **better** or **no detectable effect**: the planner stays.
- **worse** (pooled 95% CI below zero AND behind in both seasons): run ONCE on
  2022-23 and 2023-24. If it is behind in both there too, live chip timing
  switches to the fixture rule.

## Descriptive only
Chip points per season for each policy (what the simulator's no-chip totals
leave out); each chip's average realised gain; hindsight's margin over both
policies; chips left unplayed at a deadline; how often the planner's week
matched the fixture rule's. Nothing is decided from these.

## Limits, stated now
- The planner values later weeks on the squad as it stands; live, it uses the
  transfer plan's squads for the first six weeks.
- A Free Hit week still makes that week's normal transfer in the simulated
  squad. In FPL it would wait a week, with the free transfer banked. The same
  for every policy.
- Both policies read the whole fixture calendar, including doubles that in
  real life are announced only weeks ahead.
- Six chip decisions per season-seed is a small sample. "No detectable
  effect" is a likely result and would mean the test can't tell, not that
  timing doesn't matter.
