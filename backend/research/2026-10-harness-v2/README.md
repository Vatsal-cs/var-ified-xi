# Harness v2 — October 2026 results

Per-gameweek results behind the re-measured evidence ledger (README, handbook §8).
Every file is `data_engine.evaluation` input; the commit that produced them is in
each file's `commit` field (`aaab9eb`, plus the fixes committed alongside these
files).

## Reproduce the verdicts

From `backend/`:

```bash
D=research/2026-10-harness-v2

# Backtest ledger claims — 5 seeds, both tuning seasons
python -m data_engine.evaluation $D/bt_new_*.json --reference production

# Hit-margin sweep and procedures — season simulator, 3 seeds
python -m data_engine.evaluation $D/sim_new_*.json --reference production --block 4

# Harness fixes, one at a time (production under each old/new setting)
python -m data_engine.evaluation $D/bt_new_*.json $D/bt_old_*.json $D/bt_dgw_*.json $D/bt_av_*.json
python -m data_engine.evaluation $D/sim_*.json --reference production --block 4

# The one confirmation run (pre-registered: accept only if > 0 in both seasons)
python -m data_engine.evaluation $D/conf_*.json --reference production
```

## Files

| Prefix | Harness | What |
|---|---|---|
| `bt_new_*` | backtest | production, `no_refit`, `legacy_filtered`, `odds`, `naive_form` — 5 seeds |
| `bt_old_*` | backtest | production on the pre-audit harness (`--no-availability --legacy-doubles`) |
| `bt_dgw_*` | backtest | double-gameweek fix only |
| `bt_av_*` | backtest | injury flags only |
| `bt_hindsight` | backtest | the unreachable ceiling |
| `sim_new_*` | simulator | production procedure at hit margins 0/2/4/6, never-hit, old procedure, never-transfer — 3 seeds |
| `sim_leak_*` | simulator | future prices leaking into the horizon (the old behaviour) |
| `sim_noav_*` | simulator | no injury flags |
| `sim_rules_*` | simulator | today's rules for 2025-26 (no GW16 top-up), 1 seed |
| `conf_*` | backtest | 2022-23 and 2023-24, the held-back seasons — used once, for `legacy_filtered` |
| `pre_dedupe/` | both | 2025-26 runs made before ten duplicated archive rows were removed. `bt_old_25` here reproduces the pre-audit totals exactly; kept as that evidence |

2024-25 simulator comparison runs (`sim_leak_24`, `sim_noav_24`) are one seed:
that season's solves often hit the 120-second limit, so three seeds would have
taken most of a day.

Runs whose 2025-26 injury flags were read before the "available, 0% chance"
artefact was cleaned (see `availability_data.py`) are not included — they
measured a bug.
