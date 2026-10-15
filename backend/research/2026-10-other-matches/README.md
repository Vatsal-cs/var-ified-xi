# Matches FPL doesn't show — result

**Shipped.** The rest-and-load inputs passed both stages of the test written
down beforehand (PREREGISTRATION.md, commit 0cde2ab): better on the tuning
seasons, and positive on both held-back seasons. `config.OTHER_MATCHES = True`.

## Data
ESPN's public JSON feed (unofficial, no key; cached, one request at a time
after it refused a burst): every Champions League, Europa League, Conference
League, League Cup and FA Cup match of every Premier League club, and every
international match, with each player's role and the venue's country. Linked
to FPL players by name inside each club's season squad: 96.7-98.2% of
regulars. Finished seasons are packed into `backend/data/other_matches/` so
the cloud refresh never refetches them.

## Primary — tuning seasons, 5 seeds (`evaluation.txt`)

| Variant | 2024-25 | 2025-26 | Pooled, 95% CI | Runs ahead | Verdict |
|---|---:|---:|---:|---:|---|
| other_matches (rest and load) | +67 | +20 | **+87** [+13, +159] | 9 / 10 | **better** |
| other_matches_form (+ goals, shots in those games) | +69 | +12 | +81 [−4, +168] | 9 / 10 | no detectable effect |

Brier P(60+) improved a little (0.0889 → 0.0887, 0.0788 → 0.0785); MAE flat.

## Confirmation — held-back seasons, run once (`confirmation.txt`)

| | 2022-23 | 2023-24 | Rule | |
|---|---:|---:|---|---|
| other_matches | **+43** | **+11** | > 0 in both | ✅ shipped |

Pooled +54 [−74, +184]: smaller and less certain than on the tuning seasons,
as expected for the variant picked on them, but the same sign in every season.

## What the model uses
In a 2025-26 fit, the new inputs carry 2.6% of the minutes model's gain and
9.4% of the points model's, mostly the midweek schedule (days since the last
cup/European game, days until the next). Part of that is fatigue and
rotation; part is simply which clubs are in Europe — the stronger sides — a
useful signal in 2026-27, when FPL publishes no team strengths. Whether the
player started midweek and his international load carry less, but count.

## Reproduce
    cd backend
    python research/2026-10-other-matches/download.py      # fills the ESPN cache
    bash research/2026-10-other-matches/run.sh             # tuning seasons
    bash research/2026-10-other-matches/run_confirm.sh     # held-back seasons, once
    python -m data_engine.evaluation research/2026-10-other-matches/om_*.json --reference production
