#!/bin/bash
# Stale-ratings test: 2025-26 with 2024-25 as prior, 5 seeds, all at once.
cd "$(dirname "$0")/../.."
for seed in 42 7 13 101 2024; do
  OMP_NUM_THREADS=2 venv/bin/python -m data_engine.backtest --seasons 2025-26 --prior-seasons 2024-25 \
    --variants live_ratings lagged_ratings --seeds $seed --bag-size 1 \
    --out research/2026-10-stale-ratings/sr_25_s${seed}.json \
    > research/2026-10-stale-ratings/log_sr_25_s${seed}.txt 2>&1 &
done
wait
