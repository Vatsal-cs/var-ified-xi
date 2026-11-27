# Model audit — November 2026

Asked after GW11 2026-27: the user (567 points GW2-10, joined in GW2, about
2M of 11.3M after allowing for GW1) wanted the whole model studied, not
just their own theories: what it predicts, where it goes wrong, and whether
a better way to predict exists.

**What was done**
- The current model was replayed walk-forward, keeping every
  player-gameweek's projection next to the result. Each gameweek it was
  retrained on what was known before that deadline.
- Seasons: 2023-24, 2024-25 and 2025-26, plus 2026-27 GW2-10 (about 91,000
  rows).
- The replays ran on GitHub Actions (`.github/workflows/audit.yml`, using
  `research/2026-10-projection-bias/collect.py`).
- The live decisions were checked against the git history of
  `optimized_team.json` and the public FPL entry.
- Published FPL forecasting work was surveyed.

## Findings, ranked by points at stake

| # | Finding | Seasons it holds in | Status |
|---|---|---|---|
| 1 | **Early-season after-a-haul over-rating.** Projected 3+ straight after a 10+ match, GW2-14: −0.88 / −1.18 / −0.91 / −0.20 a match. Among each week's top 10 projections: −1.7 to −2.6 (−0.96 live), against −0.3 to −0.8 for everyone else. These are the players the planner buys and captains (Fernandes 8.3 in GW3 2026-27, scored 2). | all four | tested: −7 [−36, +19], −21 / +14, **not used** (`2026-11-haul-dampen`) |
| 2 | **One regressor on total points.** A total mixes events that score differently by position (a goal is 6/5/4, a clean sheet 4/1/0). Published forecasters (OpenFPL, commercial services) model the parts; this repo never had. | structural | tested: −22 [−149, +103], +10 / −32, **not used** (`2026-11-components`) |
| 3 | **Captaincy, 2026-27.** The live captains scored 50 over GW2-10; Haaland every week would have scored 68. Most of the gap was GW2-6, before the October fixes (ownership read as 0 in training, an age leak). Replayed with today's model, the top projection averages 6.9 a week over GW4-10. | live only | crowd captain already tested, no effect (`2026-10-captain-crowd`) |
| 4 | **Bench points.** 124 points sat on the bench over GW2-10 (14 a week); top-10k managers leave about 10 (`2026-10-top-gap`). The cause is the GW2 squad builder valuing bench players; a planned Wildcard gives a lean bench. | live | bench weight already tested, no effect (`2026-10-bench-weight`) |
| 5 | **The top 3 projections each week run high**: −0.43 / −1.25 / −1.95 / −1.18. | all four | pulling them back was tested; it changes almost no picks (`2026-10-projection-shrink`) |
| 6 | **Back after missing a match**: −0.64 / −0.79 / −0.73 (about 35 cases a season). | three archive seasons | small; not tested |
| 7 | **Points far above chance quality** (6+ a match on low xGI): −0.38 / −0.10 / −0.98, +0.05 live. | mostly | small samples; not tested |

`slices.txt` has every slice by season, `top10.txt` the top-10 split,
`captains.txt` the captain table, and `live_detail.txt` this season's
biggest misses both ways.

## What is fine

- **Start chance is calibrated.** Relevant players are predicted 84-85% to
  play 60+, and they did 84-87% of the time.
- **Points if he plays run slightly high,** by 0.1-0.3 in archive seasons,
  calibrated live.
- **Proven scorers are not marked down.** This season's top 10 scorers so
  far were projected 4.24 a week and scored 4.23.
- **Team and position misses don't persist.** Brighton's +2.3 a match this
  season and midfielders −0.3 look like biases. But a team's miss in GW2-6
  doesn't predict its miss in GW7-10: correlation +0.07 live, −0.26 to
  +0.20 in past seasons. Position patterns flip sign between seasons.
  Correcting either would be fitting noise.
- **The model is far better than chasing form over a season.** Best 15 each
  week by projection vs by last-5 average (no prices), points a week
  (`rules.txt`):

  | | 2023-24 | 2024-25 | 2025-26 | 2026-27 GW4-10 |
  |---|---:|---:|---:|---:|
  | model | 73.7 | 79.6 | 76.2 | 73.7 |
  | last-5 form | 61.9 | 64.0 | 59.1 | 74.4 |

  Early in a season the two are level. This is when the 2026-27 frustration
  came from.

## Results of the tests

Both were pre-registered and run in one backtest: 5 seeds × 2 tuning
seasons, paired against lagged_ratings (run 44948255122).

| Variant | Pooled | 2024-25 | 2025-26 | Verdict |
|---|---:|---:|---:|---|
| points_by_part | −22 [−149, +103] | +10 | −32 | no detectable effect |
| haul_dampen | −7 [−36, +19] | −21 | +14 | no detectable effect |

## Verdict

Nothing in the model is broken.
- Its one consistent miss (early-season after-a-haul) is real, but
  correcting it doesn't win points.
- The most promising method from the literature (points by part) is no
  better.
- Together with the earlier rejected variants, this says the projection
  model is at the ceiling of the free public data it uses.
- The gap to top managers is mostly the variance of a single season, not a
  fixable error. The October audit found none of today's top-10k managers
  finished top 10k last season.

**Recommendation:** stop changing the predictor. Keep the live model as it
is, and present this audit, misses included, as the work.

## Reproduce

```bash
gh workflow run audit.yml --ref audit/model-2026-11        # the four replays
gh run download <run> -D rows                               # rows_<season>.csv
python research/2026-11-model-audit/slices.py live=rows/rows-live/.../rows_live.csv 2023-24=... 2024-25=... 2025-26=...
python research/2026-11-model-audit/top10.py rows           # expects rows/<season>/research/2026-10-projection-bias/rows_<season>.csv
python research/2026-11-model-audit/rules.py <rows csv> 4 38
python research/2026-11-model-audit/snapshots.py > research/2026-11-model-audit/snapshots.txt   # from the repo root
python research/2026-11-model-audit/captains.py
```

Sources surveyed: [OpenFPL (Groos, 2025)](https://arxiv.org/abs/2508.09992),
[Ramezani & Dinh, data-driven FPL team selection (2025)](https://arxiv.org/abs/2505.02170),
[AIrsenal](https://github.com/alan-turing-institute/airsenal).
