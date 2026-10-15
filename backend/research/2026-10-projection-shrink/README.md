# Pulling the top projections back — result

**No detectable effect. The shrink stays off.** Pre-registered in
PREREGISTRATION.md (commit e5da274) before any full run.

Out of sample, the points-if-60+ projection is too spread out: the top
projections come in low and the bottom ones high
(research/2026-10-distributions). Pulling each projection toward its
position's average by a factor fitted on other seasons (0.60-0.69) fixes that
spread. The question was whether it also wins points.

## Primary — backtest, 5 seeds × 2 tuning seasons (`evaluation.txt`)

| Variant | 2024-25 | 2025-26 | Pooled, 95% CI | Runs won | Verdict |
|---|---:|---:|---:|---:|---|
| shrink (primary, one factor) | +20 | −21 | **−1** [−54, +53] | 3 / 10 | no detectable effect |
| shrink_pos (per position) | +5 | −26 | −21 [−78, +40] | 4 / 10 | no detectable effect |

Neither is "better", so nothing goes to the held-back seasons and
`config.CONDITIONAL_SHRINK` stays `None`. Accuracy improves a little (MAE
0.996 → 0.993 and 0.911 → 0.906), as a calibration fix should, but it barely
changes which players are picked, so the points don't move.

## Descriptive — 2026-27 GW2-6 replay (`replay_2026.txt`)

| | GW2-6 squad points (mean) | per seed | MAE |
|---|---:|---|---:|
| production | 347.0 | 344, 367, 330 | 1.180 |
| shrink | 354.0 | 365, 364, 333 | 1.175 |
| shrink_pos | 345.3 | 347, 357, 332 | 1.177 |

Five weeks, three seeds: inside the noise either way.

## What it means

The model's top projections really are too high, but its ranking of players
is about right, and the squad comes from the ranking. Together with the price
test (research/2026-10-price-feature) and the player-type bias test
(research/2026-10-projection-bias), none of the suspected reasons for
"expensive names over cheaper in-form players" costs points on the evidence.

## Reproduce

    cd backend
    bash research/2026-10-projection-shrink/run.sh
    python -m data_engine.evaluation research/2026-10-projection-shrink/ps_*.json --reference production
    python research/2026-10-projection-shrink/replay_2026.py
