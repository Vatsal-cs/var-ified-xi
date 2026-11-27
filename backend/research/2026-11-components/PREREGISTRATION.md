# Points by part — pre-registration
Written 2026-11-21, before any run. Runs on GitHub Actions.

Why: the model's second stage predicts a player's total points in one go
(given 60+ minutes). A total mixes events that score differently by
position: a goal is 6 for a defender, 5 for a midfielder, 4 for a forward,
and a clean sheet is 4, 1 or 0. Published FPL forecasters mostly predict the
parts instead and add them up with FPL's scoring. No study in this repo has
tried it. Found in the November 2026 model audit (research/2026-11-model-audit),
after a live replay showed the worst projections were premium attacking
midfielders straight after a big game (Fernandes 8.3 in GW3, scored 2).

## Variant (backtest.py)
- points_by_part: lagged_ratings, but stage 2 fits five models on 60+
  minute rows, with the same features and tree settings as the points
  regressor: goals (Poisson), assists (Poisson), clean sheet (logistic),
  bonus (Poisson), and the rest (squared error; total points minus
  appearance, goals, assists, clean sheet and bonus points, so it holds
  saves, goals conceded, defensive contributions and cards). The expected
  points if he plays 60+ are 2 + goal points × goals + 3 × assists +
  clean-sheet points × P(clean sheet) + bonus + rest. The parts add up to
  total points exactly, so nothing is dropped. The minutes model, the
  shrink, the calibration, the cameo values and the planner are unchanged.
- Reference: lagged_ratings.

## Run
Seeds 42, 7, 13, 101, 2024. Seasons 2024-25 (trained on itself) and 2025-26
(plus 2024-25). --bag-size 1. Pooled with data_engine.evaluation,
--reference lagged_ratings, --block 4.

## Decision
- Ahead in BOTH tuning seasons and the pooled 95% interval above zero:
  ONE run on the held-back 2022-23 and 2023-24 with the same settings. It
  ships as production only if it is ahead in both held-back seasons too.
- Anything else: not used, recorded as a rejected variant with its numbers.
