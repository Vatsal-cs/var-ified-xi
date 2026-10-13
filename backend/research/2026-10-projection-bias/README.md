# Projection bias by player type — result

**No bias found. Nothing to fix.** Pre-registered in PREREGISTRATION.md
(commit 40a80a3) before any run.

The question came from 2026-27 GW6: the model started Murillo (4.29, a
steady defensive-contribution scorer) over De Cuyper (2.74) and João Pedro
(3.45), who scored 15 and 12 from the bench. Were attackers, players coming
back from one missed match, or players whose points came in one or two big
games being projected too low *as a rule*?

## Verdicts

| Test | Statistic | Result | Verdict |
|---|---|---|---|
| T1 attackers vs steady defenders (2025-26) | residual(attackers) − residual(steady defenders) | **+0.02** [−0.43, +0.41] · n 1638 / 212 | no bias found |
| T2 one missed match, fit at the deadline (pooled) | actual 60+ rate − predicted P(60+) | **−0.06** [−0.12, −0.00] · n 436 | no bias found — wrong direction for the suspicion |
| T3 points from one big game vs spread out (pooled) | residual(haul share ≥ 0.5) − residual(≤ 0.35) | **+0.12** [−0.23, +0.51] · n 769 / 924 | no bias found |

Per season: T2 −0.02 (2024-25) and −0.11 (2025-26); T3 +0.13 and +0.10.
Same sign as pooled in every case.

- **T1.** Both groups are projected within 0.1 points of what they scored:
  attackers 3.83 projected vs 3.93 actual, steady defenders 3.74 vs 3.83.
  Splitting into chance of playing and points-if-he-plays, both halves are
  calibrated for both groups.
- **T2.** The suspicion was that one 0-minute week cuts a fit regular's start
  chance too far. It's the other way: such players started 48% of the time
  against a predicted 54%. If anything the model is slightly *generous* to
  them. (Not a pre-registered direction, so no change is made on it.)
- **T3.** Players whose recent points came from one big game score about what
  the model expects; it isn't writing them off.

## Descriptive

By position, residuals sit within ±0.15 points a match in both seasons
(results.json, analysis_output.txt). The live 2026-27 GW2-6 replay (current
model, last season's team ratings, no deadline injury flags) shows the same
picture; its groups are small and carry no verdict.

**The live GW6 decision, replayed with the fixed model:** Murillo 3.86,
João Pedro 3.57, De Cuyper 3.18. If João Pedro played 60+, the model
expected *more* from him than from Murillo (4.64 vs 4.39); the whole gap was
his start chance (74% vs 87%) after missing GW5.

**Close calls are close (post hoc, not pre-registered).** Two players in the
same gameweek, both projected 2.5+, ties left out — how often the higher
projection outscores the lower:

| Projection gap | Pairs | Higher one wins |
|---|---:|---:|
| 0–0.5 | 231,240 | 52% |
| 0.5–1 | 156,025 | 57% |
| 1–1.5 | 86,667 | 60% |
| 1.5–2 | 42,394 | 64% |
| 2–3 | 34,433 | 68% |
| 3+ | 30,496 | 75% |

A 0.3-point start/bench call like Murillo vs João Pedro is barely better than
a coin flip in a single week; it pays off over a season, not every week.

## Reproduce

    cd backend
    python research/2026-10-projection-bias/collect.py 2024-25
    python research/2026-10-projection-bias/collect.py 2025-26 --prior 2024-25
    python research/2026-10-projection-bias/collect.py live
    python research/2026-10-projection-bias/analyze.py

collect.py writes rows_*.csv (about 11 MB, not committed); the bootstrap is
seeded, so analyze.py reproduces these numbers exactly.
