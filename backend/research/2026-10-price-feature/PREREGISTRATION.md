# Price as a model input — pre-registration
Written 2026-10-14 20:20 MDT, before any full run (a 4-gameweek smoke test
checked only that the variants run).

Why: in GW7 the Wildcard squad started Thiago (£7.8m, 14 points in 6 games).
The biggest single push to his projection was his price (+0.7 points if he
plays): the model learned that expensive players score more, and a price set
before the season partly carries last season's reputation. Ownership
(selected_by_percent) is a second reputation signal. Are the projections
better without them?

## Variants (data_engine/backtest.py)
- **no_price** (primary): production with `now_cost` removed from the model's
  inputs. The optimizer still sees prices — budget is unchanged.
- **no_price_own** (secondary): `now_cost` and `selected_by_percent` removed.

## Primary — backtest, points
production vs each variant, seeds 42, 7, 13, 101, 2024; 2024-25 (trained on
itself) and 2025-26 (plus 2024-25); gameweeks 2-38; injury flags on; one
model per fit (--bag-size 1, both sides — the bag only averages seeds, and
the team-form test ran the same way). Pooled with data_engine.evaluation.

**ACCEPT** a variant on the tuning seasons only if the verdict is "better"
(pooled 95% CI above zero AND ahead in both seasons). If both are better,
the one with the larger pooled difference goes forward. Then run it ONCE on
2022-23 (trained on itself) and 2023-24 (plus 2022-23), 5 seeds; ship
(remove the column from config.FEATURE_COLUMNS) only if the paired
difference is > 0 in both. Anything else: price stays, and the result is
recorded either way.

## Descriptive only
- MAE, rank correlation and Brier P(60+) per variant.
- The 2026-27 GW2-6 replay (current model setup, last season's team
  ratings), seeds 42, 7, 13 — the season you're watching, too small and too
  seen to decide anything.
