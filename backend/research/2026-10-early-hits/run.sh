#!/bin/bash
# Paired branch test, GW2-8: production vs no hits before GW9. 2 seasons x 3 seeds.
cd "$(dirname "$0")/../.."
job() {
  season=$1; seed=$2
  case $season in
    2024-25) prior=""; tag=24;;
    2025-26) prior="--prior-seasons 2024-25"; tag=25;;
    2022-23) prior=""; tag=22;;
    2023-24) prior="--prior-seasons 2022-23"; tag=23;;
  esac
  OMP_NUM_THREADS=2 venv/bin/python -m data_engine.season_sim --seasons $season $prior \
    --policies production --branch production:production_early_nohits --end-gw 8 \
    --seeds $seed --bag-size 1 \
    --out research/2026-10-early-hits/eh_${tag}_s${seed}.json \
    > research/2026-10-early-hits/log_eh_${tag}_s${seed}.txt 2>&1
}
export -f job
seasons=${SEASONS:-"2024-25 2025-26"}
for season in $seasons; do for seed in 42 7 13; do echo "$season $seed"; done; done \
  | xargs -P 3 -L 1 bash -c 'job "$0" "$1"'
