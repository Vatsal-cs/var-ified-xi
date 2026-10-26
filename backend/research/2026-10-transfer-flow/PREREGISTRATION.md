# Transfer flow as a model input — pre-registration
Written 2026-10-26 MDT, after step 1 and before any backtest run.

Why (2026-27 GW2-8 audit against 50 top-10k managers): the gap was mostly
which players were owned (−73 points) and captained (−31), Haaland above all.
Ownership as an input was worth +122. It is the crowd's settled view. What
the crowd changed its mind about *this week* (a leaked lineup, a new penalty
taker, a knock) shows up first in transfers, and the model never sees them.

## Step 1 (done, `step1.py`, `step1_output.txt`)
Out-of-sample projections from research/2026-10-projection-bias, players
projected 2+, GW3+. Residual (scored − projected) for players being bought
(net transfers > 0.25% of the gameweek's transfers in) minus quiet players
(|net| ≤ 0.25%), block-bootstrapped by gameweek:

| Season | bought − quiet | 95% CI |
|---|---:|---|
| 2024-25 | +0.29 | [+0.05, +0.52] |
| 2025-26 | +0.15 | [−0.05, +0.33] |

Same sign in both, mostly through minutes (played-60 rate above the model's
P(60+) by 0.05-0.09 for bought players, ~0.01 for quiet ones). Enough to
justify step 2.

## Variant (backtest.py "transfer_flow")
Production plus `transfer_flow`: net transfers in before the deadline as a
percent of all that gameweek's transfers in. Archive: `transfers_balance /
Σ transfers_in` per gameweek (each player once per round). This season's
history rows: the same from FPL's per-gameweek fields. Live: `transfers_in_event
− transfers_out_event` over `Σ transfers_in_event` at run time (checked: a
snapshot two days before GW8's deadline correlates 0.96 with the final GW8
counts). GW1 is 0 everywhere (no transfers before it).

## Primary — backtest, points
production vs transfer_flow, seeds 42, 7, 13, 101, 2024; 2024-25 (trained on
itself) and 2025-26 (plus 2024-25); --bag-size 1. ACCEPT only if "better"
(pooled 95% CI above zero AND ahead in both seasons); then ONCE on 2022-23
and 2023-24, logged in config's "Uses so far"; ship only if > 0 in both.
Otherwise TRANSFER_FLOW_FEATURE stays False and the result is recorded.

## Secondary (reported, not decisive)
MAE, rank correlation, minutes-model Brier score.
