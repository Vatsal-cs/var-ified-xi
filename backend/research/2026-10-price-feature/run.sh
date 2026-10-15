#!/bin/bash
# Tuning-season runs for the price-feature test: 2 seasons x 5 seeds, four at a time.
cd "$(dirname "$0")/../.."
job() {
  season=$1; seed=$2
  case $season in
    2024-25) prior=""; tag=24;;
    2025-26) prior="--prior-seasons 2024-25"; tag=25;;
  esac
  OMP_NUM_THREADS=2 venv/bin/python -m data_engine.backtest --seasons $season $prior \
    --variants production no_price no_price_own --seeds $seed --bag-size 1 \
    --out research/2026-10-price-feature/pf_${tag}_s${seed}.json \
    > research/2026-10-price-feature/log_pf_${tag}_s${seed}.txt 2>&1
}
export -f job
for season in 2024-25 2025-26; do for seed in 42 7 13 101 2024; do echo "$season $seed"; done; done \
  | xargs -P 4 -L 1 bash -c 'job "$0" "$1"'
