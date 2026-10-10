# Bench weight — pre-registration
Written 2026-10-10 10:57 MDT, before any run.

Question: does counting bench players for less (BENCH_WEIGHT 0.12 now) move money
into the starting XI and score more? Prompted by ~£22m and ~18 points a week on
the live team's bench.

Primary — backtest (squad rebuilt weekly), bench weights 0.06 / 0.03 / 0.01 vs
0.12, each squad picked from the SAME predictions; seeds 42, 7, 13, 101, 2024;
2024-25 and 2025-26; single model per fit (--bag-size 1: the optimizer is what's
compared). Standard verdict rules (evaluation.py).

Secondary — season_sim, production vs production_bench0.03: paired branch test
and full season, seeds 42, 7, 13, both seasons. Must not be "worse".

ACCEPT the weight with the largest pooled backtest gain among those that are
"better" there and not "worse" in the simulator; then run it ONCE on 2022-23 and
2023-24 (backtest, 5 seeds) and ship it (config.BENCH_WEIGHT) only if its paired
difference is > 0 in both. If none passes, BENCH_WEIGHT stays 0.12.

The GW7 Wildcard squad is built with whatever BENCH_WEIGHT stands afterwards.
commit 736710c
