#!/bin/bash
# The single pre-registered confirmation run on the held-back seasons. Ran on
# GitHub Actions (backtest.yml), not locally:
#   gh workflow run backtest.yml -f seasons="2022-23 2023-24" \
#     -f variants="lagged_ratings lagged_long_form" -f seeds="42 7 13 101 2024" \
#     -f reference=lagged_ratings -f extra_args="--bag-size 1"
# Its artifacts are saved here as conf_{22,23}_s{seed}.json. The local equivalent:
cd "$(dirname "$0")/../.."
job() {
  season=$1; seed=$2
  case $season in
    2022-23) prior=""; tag=22;;
    2023-24) prior="--prior-seasons 2022-23"; tag=23;;
  esac
  OMP_NUM_THREADS=2 venv/bin/python -m data_engine.backtest --seasons $season $prior \
    --variants lagged_ratings lagged_long_form --seeds $seed --bag-size 1 \
    --out research/2026-10-long-form/conf_${tag}_s${seed}.json \
    > research/2026-10-long-form/log_conf_${tag}_s${seed}.txt 2>&1
}
export -f job
for season in 2022-23 2023-24; do for seed in 42 7 13 101 2024; do echo "$season $seed"; done; done \
  | xargs -P 4 -L 1 bash -c 'job "$0" "$1"'
