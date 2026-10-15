# Price as a model input — result

**Price stays.** Taking it out loses points in every run. Pre-registered in
PREREGISTRATION.md (commit 1d7ddfd) before any full run.

The question came from the GW7 Wildcard squad starting Thiago (£7.8m, 14
points in 6 games), where the single biggest push to his projection was his
price. Is price a stale reputation signal the model would be better without?

## Primary — backtest, 5 seeds × 2 tuning seasons (`evaluation.txt`)

| Variant | 2024-25 | 2025-26 | Pooled, 95% CI | Runs won | Verdict |
|---|---:|---:|---:|---:|---|
| no_price (primary) | −61 | −67 | **−128** [−287, +30] | 0 / 10 | no detectable effect, every run behind |
| no_price_own | −22 | −77 | −99 [−249, +46] | 2 / 10 | no detectable effect |

Neither is "better", so by the rule written beforehand nothing goes to the
held-back seasons and price (and ownership) stay as inputs. Prediction
accuracy agrees: MAE 0.996 → 1.021 (2024-25) and 0.911 → 0.920 (2025-26)
without price.

## What it means

Across players, price carries real information the form features don't —
FPL sets it from a whole season of quality, and the model uses it as a
steadying prior. For an individual whose season has gone badly (Thiago),
that prior is stale, and the projection leans on it more than his recent
games deserve. That is a per-player mistake, not a reason to drop the
input: on average it earns points.

The related finding — the top projections run high, which favours the
expensive players most — is tested separately (research/2026-10-projection-shrink).

## Descriptive — 2026-27 GW2-6 replay (`replay_2026.txt`)

Seeds 42, 7, 13, one model per fit, squad rebuilt each week:

| | GW2-6 squad points (mean) | per seed | MAE |
|---|---:|---|---:|
| production | 347.0 | 344, 367, 330 | 1.180 |
| no_price | 342.0 | 322, 347, 357 | 1.184 |
| no_price_own | 338.0 | 350, 333, 331 | 1.185 |

Same direction as the past seasons, inside the noise of five weeks.

## Reproduce

    cd backend
    bash research/2026-10-price-feature/run.sh
    python -m data_engine.evaluation research/2026-10-price-feature/pf_*.json --reference production
    python research/2026-10-price-feature/replay_2026.py
