# What top managers have that the model doesn't — October 2026 audit

Asked after GW8 2026-27: managers at the top of the Canada league (608-632
points, ~77 a gameweek) were scoring far more every week. Where do their
points come from, and what is the model missing?

Data: FPL's public API. 50 managers sampled from the overall top 10k after
GW8 (their GW1-8 picks and histories), the Canada league's top 50, and the
model's own picks at each deadline (`frontend/public/optimized_team.json` in
git history). Raw pulls aren't committed; `decomp.py` and `eo_gap.py` take the
directory they were saved in.

## 1. Today's leaders are mostly on a hot streak

| Group (after GW8 2026-27) | 2025-26 finish: median rank | top 10k last season | outside top 1M |
|---|---:|---:|---:|
| Overall top-10k sample (n 48) | 766,699 | 0% | 38% |
| Canada top 50 (n 47) | 531,495 | 0% | 30% |

None finished top 10k last season. What a top-10k *season* takes, from the
same managers' histories: ~2,400 points in 2025-26 and ~2,600 in 2024-25,
i.e. **63-68 a gameweek including chips**. Nobody holds 77.

## 2. Where the GW2-8 gap came from (top-10k sample)

| Per manager, GW2-8 | Top 10k | You | Model's own picks |
|---|---:|---:|---:|
| Total | 533 | 446 | 412 |
| XI points (base) | 445 | 400 | — |
| Armband (extra) | 71 | 46 | — |
| Chips | 17 | 0 | 0 |

Model vs top 10k by player (ownership × points): **Haaland −34 not owned
GW2-6, −19 not captained**, Calafiori −28, Mbeumo −16; captaincy also
Fernandes −12 (GW2) and João Pedro −8. Chip points are timing: the first-half
Bench Boost, Triple Captain and Free Hit are still in hand (projected 26.5).

The live planner kept Fernandes as captain through GW3-8 of its plans and
scheduled Haaland for GW9. Today's model, replayed on GW2-6
(research/2026-10-projection-bias `rows_live.csv`), ranks Haaland first in
GW4 and GW5. Part of the early gap was model bugs fixed since (ownership 0 in
training, the age leak).

## 3. Start/bench calls

Best XI from your own 15 in hindsight minus the XI you fielded (no chips):
**you 10.8 points a gameweek, top 10k 6.0** (bench points 15.0 vs 9.9).
Bench cost isn't the difference (top-10k median £22.6m, you £24.1m).

## 4. Early-season over-reaction (your "bias" complaint)

Out-of-sample, players projected 2+ straight after a 10+ haul scored less
than projected in every GW2-14 bucket of both seasons (−0.2 to −1.8 a match),
and were calibrated after GW14. The season-wide test in
research/2026-10-projection-bias pooled this away. In the simulator, the hits
this drives were the worst decisions: GW3 2024-25 lost 33-45 points in all
three seeds (De Bruyne projected 10.5 after his start).

## What was tested

| Idea | Where | Result |
|---|---|---|
| Transfer flow (net transfers before the deadline) as an input | research/2026-10-transfer-flow | −47 [−127, +35], behind in both seasons — not used |
| No hits before GW9 | research/2026-10-early-hits | +41 in 2024-25 (one GW3 decision), 0 in 2025-26 — not adopted |
| Choosing the XI after autosubs | research/2026-10-lineup | −37 [−75, −4], behind in both — worse |
| Season stage (matches_played) as an input | research/2026-10-season-stage | −13 [−70, +44], +34 / −47 — not used |
| Planner horizon decay 0.95 | research/2026-10-horizon-decay | +60 [−109, +239], +110 / −49 — not adopted |

None passed. What the audit does leave standing: the model plays like a
roughly top-1M manager (simulator ~56 a gameweek before chips, against ~63-68
for a top-10k season), the transfer-constrained planner gives up 6-8 a
gameweek against the same model with unlimited transfers, and early-season
projections after a big game run high. Those are where the next tests belong.
