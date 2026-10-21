<div align="center">

# VAR-ified XI

**Machine-checked. Math-approved. Your FPL squad, reviewed.**

A Fantasy Premier League engine that predicts every player's points with XGBoost, solves for the best transfer under the real rules with a Mixed-Integer Linear Program — and refuses to ship anything that can't prove it scores more points.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![XGBoost](https://img.shields.io/badge/XGBoost-ML-EB1834?style=flat-square)](https://xgboost.ai)
[![PuLP](https://img.shields.io/badge/PuLP-MILP_Solver-2E8B57?style=flat-square)](https://coin-or.github.io/pulp/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org)
[![Tailwind](https://img.shields.io/badge/Tailwind-CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Vercel](https://img.shields.io/badge/Deployed_on-Vercel-black?style=flat-square&logo=vercel)](https://vercel.com)

[Live dashboard](https://var-ified-xi.vercel.app) · [Report a bug](https://github.com/Vatsal-cs/var-ified-xi/issues)

</div>

---

## What this actually does

Most "FPL AI" projects sort players by points-per-million and call it a day. This one treats FPL as two separate problems, because it is two separate problems.

**Prediction** — how many points will this player score? **Decision** — given what I already own, my bank and my free transfers, what should I actually do? A perfect predictor paired with a bad decision rule loses to a mediocre predictor paired with a good one, because the decision rule is the part that touches your team.

So there are two models and two test harnesses, and neither can flatter the other.

### 1 · Prediction — two models, not one

Rotation risk is the biggest source of error in fantasy football, and a flat regressor smears it together with quality. A player projected at 2.0 might be a certain starter who is mediocre, or a brilliant player who might not feature. Those demand opposite decisions.

```
Stage 1   minutes classifier   P(didn't play) · P(cameo) · P(60+ mins)
Stage 2   points regressor     E[points | played 60+]

          xP = P(full) × E[pts|full] + P(cameo) × cameo_avg[position]
```

Trained on this season plus three past ones — about 87,000 real gameweek results. Five copies are trained with different random seeds and their projections averaged, so one unlucky seed can't swing the picks.

### 2 · Decision — a solver, not a heuristic

A PuLP/CBC Mixed-Integer Linear Program solves the 15-man squad, the starting XI, the captain and the transfers across **six gameweeks at once**, under every real constraint: £100.0m budget, 2/5/5/3 quota, legal formation, max 3 per club, one free transfer a week (bank up to five), −4 per extra.

The answer is *provably optimal given the predictions*. Not a top-N sort.

### Two modes

| Command | Answers |
|---|---|
| `python main.py` | "What's the best possible squad?" — GW1, a wildcard, a fresh start |
| `python main.py --team-id 1234567` | "Given the team I own, what should I change?" — every other week. Reads your public team, works out your bank, sell prices and free transfers, plans six gameweeks ahead |

---

## Nothing ships on intuition

A change ships when it scores more **realized** points — and when that gain is bigger than the noise. Ideas that lose stay in the codebase as named, re-runnable variants with their exact numbers, so a rejected idea can never quietly return as a fresh insight.

### How big is the noise?

Changing *nothing* but XGBoost's random seed moves a two-season backtest by up to **175 points**, with accuracy identical to three decimals. The solver turns tiny prediction differences into different squads. The old rule — "score more in every season, on one run" — passed a change that does nothing **half the time**.

So every comparison now runs on several seeds and reports a paired, block-bootstrapped 95% interval, with the verdict rule written down before the run:

| Verdict | Rule |
|---|---|
| **better** | pooled interval above zero *and* ahead in every season |
| **worse** | pooled interval below zero *and* behind in every season |
| **no detectable effect** | anything else — the harness can't tell, which is not the same as "rejected" |

Changes are chosen on 2024-25 and 2025-26. 2022-23 and 2023-24 are held back: a change that comes out **better** is run on them **once**, against a criterion written down first, and ships only if it keeps its sign.

### The evidence ledger, re-measured

Every verdict below was first decided on **one seed**. The October 2026 audit re-ran the biggest claims on the corrected harness — 5 seeds per season for the backtest, 3 for the simulator — and most of them didn't survive as stated:

| Claim | First measured (1 seed) | Re-measured, pooled 95% CI | Verdict |
|---|---:|---:|---|
| A model at all, vs last-5 average | +19% | **+614** [+361, +876] · +15% | ✅ **better** |
| Hit must gain 8, not 6 | +299 | −1 [−92, +97] | no detectable effect |
| Refit on all data after validating | +127 | +43 [−75, +171] · ahead 8 of 10 seed-seasons | no detectable effect |
| Betting-odds features | −32 | +15 [−82, +107] | no detectable effect |
| Team strength from recent xG instead of FPL's ratings (new) | — | 2025-26 −153 [−276, −24]; 2026-27 replay 267 vs 292 | ❌ worse — last season's FPL ratings stay |
| Count bench players for less than 12% (new) | — | backtest +15 to +25, CIs span zero · simulator −36 [−85, +11] | no detectable effect — stays 12% |
| Average five models trained with different seeds (new) | — | starting XIs agreed between seeds 75–78% → 86–88% in all four seasons; points +25 [−37, +92] · held back +23 [−34, +82] | ✅ **shipped** — steadier picks, no cost |
| Injured/suspended players' later weeks by return dates and measured return curves (new) | — | +4.7 [−26, +33] · changed 11 of 222 decisions | no detectable effect — stays off |
| Projections biased by player type: attackers vs steady defenders, after one missed match, points from one big game (new) | — | +0.02 [−0.43, +0.41] · −0.06 [−0.12, −0.00] · +0.12 [−0.23, +0.51] pts per match | no bias found — nothing to fix |
| Drop price (and ownership) as model inputs (new) | — | −128 [−287, +30] · behind in 10 of 10 runs; with ownership too −99 [−249, +46] | no detectable effect, every run behind — price stays |
| Pull the top projections back toward the position average (new) | — | −1 [−54, +53] · +20 and −21 by season; per position −21 [−78, +40] | no detectable effect — stays off (accuracy a little better, picks barely change) |
| Cup, European and international matches as inputs: rest, rotation, international load (new) | — | +87 [+13, +159] · ahead in both seasons, 9 of 10 runs · held back **+43 and +11** | ✅ **shipped** |
| Form adjusted for opponent strength: schedule strength, adjusted PL form, Elo-weighted cup/European/international form (new) | — | +18 [−65, +99] · +11 [−45, +66] · −17 [−113, +87] | no detectable effect — none used |
| A second model that learns the first one's mistakes (new) | — | 2024-25 −51 [−166, +53], behind in 3 of 4 runs — stopped once it couldn't pass | not used |
| This season's team form added to the ratings (new) | — | −0.2 [−110, +112] · +41 and −41 by season | no detectable effect — not used |
| Real player ages: a live-only bug, not a test. History stores every age as 26, so only this season's rows had real ages and the trees used them to tell players apart (Henderson, 36: 2.4 → 5.1 projected) | — | never in any backtest: age is 26 in every replayed season | 🐞 **fixed**: age off, so live runs match what was tested |
| This season's team form, tested with last season's ratings as live (new) | — | +6 [−118, +123] · +13 and −7 by season · the season's own ratings were worth +107 in 2025-26 | no detectable effect — not used |
| Team ratings from betting odds, with last season's ratings as live (new) | — | +1 [−107, +111] · +4 and −3 by season | no detectable effect — not used |
| Training on stale team ratings, as the live model plays on them (new) | — | −14 [−85, +58] on 2025-26 · stale ratings themselves cost ~93 a season | no detectable effect — not used |
| Early-season tilt toward points per match played (GW1-10) (new) | — | −17.6 [−45, +9] · −11 and −7 by season, 3 of 10 runs | no detectable effect, behind in both — not used |
| Ownership as an input, actually filled in for training (it was 0 everywhere) (new) | — | **+122** [+26, +216] · ahead in both, 8 of 10 runs · held back **+65 and +14** | ✅ **shipped** |
| Club rotation rate as an input (new) | — | −19 [−80, +43] · +12 and −31 by season | no detectable effect — not used |
| Points-if-60+ calibrated to what players at each level really scored (new) | — | −29 [−123, +69] · +6 and −35 by season | no detectable effect — not used |
| Stale ratings replaced by odds-based ratings, as live (new) | — | −28 [−128, +75] · +14 and −42 by season | no detectable effect — not used |
| Form in European, cup and international games, second look (new) | — | stopped at step 1: misses +0.04 [−0.21, +0.29] for players who scored there; strong or weak opponents alike | no signal — not built |
| Split training populations, vs starters-only for both stages | +7 | starters-only **+56** [+11, +103] on the tuning seasons — then +18 and −17 on the held-back seasons | ⚠️ **unconfirmed**: split populations stay |

The one **better** on the tuning seasons was a surprise: training *both* stages on established starters only — the setting this project had rejected — beat production by 56 points, ahead in both seasons. Under the rule written before the run, it then had to keep its sign on the two held-back seasons. It didn't: +18 in 2022-23, −17 in 2023-24. It stays off. That's exactly what the held-back seasons are for — without them, production would have switched models on a result that doesn't generalise.

Not re-measured, and every one of them sits inside the ±146-point band that changing only the seed produces — so treat each as **unproven either way**, not as settled:

| Idea | One-seed result | Reasoning at the time |
|---|---:|---|
| Per-position regressors | −104 | splits the feature set too thin |
| Captain on ceiling instead of mean | −75 | upside-chasing infects the whole squad |
| Early-season shrinkage | −64 | multi-season training covers thin early weeks |
| Set-piece / penalty features | −62 | takers are just good players; already in their xG |
| Recency weighting by season | −58 | lost both seasons |
| Single flat regressor | −53 | smears rotation risk into quality |
| Differential tilt toward unowned players | ≈0 | points-neutral; buys rank variance only |

### What the audit found was being measured

The re-measurement only means something because the harnesses were fixed first. Each fix was checked for moving totals in the direction it should — a fix that moves them the wrong way points at a bug in the fix:

| Fix | Expected | Measured |
|---|---|---|
| Predict a double-gameweek player per match, not once | more points in double weeks | ✅ +94 and +43, every point of it in the 7 double weeks; +137 [+34, +273] overall |
| Freeze prices at the deadline in multi-week projections | lower simulator totals (the leak flattered them) | ✅ higher with the leak in both seasons for both procedures (+101 and +65 pooled; 7 of 8 seed-seasons) — inside the simulator's noise, so direction only |
| Pre-deadline injury flags | better accuracy | ✅ MAE 1.086 → 0.996 and 0.991 → 0.911; Brier P(60+) 0.097 → 0.089 and 0.084 → 0.079. Points: no detectable effect (−9 [−53, +33]) |
| Each season's own transfer rules | correct counts | unit tests; first-week accrual reproduces a real team |
| Simulator runs production's own decision code | identical live output | identical recommendation before and after |

The injury-flag check caught a real bug on its way through: the 2025-26 snapshots list hundreds of fit players as "available, 0% chance", which zeroed their projections until it was cleaned out.

### Bracketed so the numbers mean something

| | points per gameweek (2024-25 / 2025-26) |
|---|---|
| `naive_form` — no model, just each player's last-5 average | 57.7 / 51.9 |
| **This model** (mean of 5 seeds) | **64.6 / 61.7** |
| `hindsight` — optimise on what actually happened, unreachable | 149.0 / 154.6 |

Roughly **+15% over having no model at all** — the clearest result in the project.

> FPL's own published xP looked like an obvious third yardstick, but a squad built from the archived values scores ~99/GW — two thirds of perfect hindsight, which no pre-deadline forecast achieves. Those values are recorded after lineups are known. The comparison was dropped rather than left in looking authoritative.

---

## Two harnesses, two questions

| | `backtest.py` | `season_sim.py` |
|---|---|---|
| **Answers** | Are the *predictions* good? | Are the *decisions* good? |
| **Squad** | Rebuilt from scratch weekly, unlimited transfers | One squad carried forward all season |
| **Transfers** | Free and unlimited | That season's real rules — bank cap, top-ups, −4 per extra |
| **Prices** | As they were | Move, with half-the-rise selling |
| **Use for** | Model and feature changes | Anything in the transfer planner |

Both replay seasons gameweek by gameweek, training only on data strictly before the week being predicted, then score the chosen team against what actually happened — autosubs and captain-to-vice fallback included. Both see the injury flags FPL published **before** each deadline (from 2024-25, when snapshots begin), and both predict a double-gameweek player **per match**.

`season_sim.py` runs **the exact decision code the dashboard runs** (`planner.py`) and trains **one model per gameweek, handed identically to every policy**, so any difference in score is the decision rule and nothing else. Form, price and injury news are frozen at the deadline; fixture context is not, because the fixture list really is published months ahead.

> **Audited October 2026.** The harnesses used to play a different game from production: a 2-transfer bank in seasons that allowed 5, a decision procedure production never ran, future prices leaking into multi-week projections, double-gameweek players projected for one match and scored for two, and no injury data. All fixed, each behind a test, with the old behaviour kept as `--legacy-*` flags for one cycle. The old-harness mode reproduces the earlier numbers exactly, so the before/after is like for like.

---

## Quickstart

```bash
git clone https://github.com/Vatsal-cs/var-ified-xi.git
cd var-ified-xi/backend

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python main.py                    # best possible squad
python main.py --team-id 1234567  # transfer plan for your real team
```

Takes 5–15 minutes, most of it fetching ~660 player histories. Writes `optimized_team.json` into `backend/data/output/` and `frontend/public/`.

```bash
cd ../frontend
npm install
npm run dev                       # localhost:3000
```

**Deploy free:** push to GitHub → import into [Vercel](https://vercel.com) → set **Root Directory** to `frontend`.

### Testing a change

```bash
# model / feature changes — five seeds, results kept as JSON
python -m data_engine.backtest --augment --variants production your_variant \
       --seeds 42 7 13 101 2024 --out bt.json

# transfer-planner changes
python -m data_engine.season_sim --augment \
       --policies production your_policy --seeds 42 7 13 --out sim.json

# a planner change, paired: each week the candidate decides from production's
# exact position and both are scored over the next six weeks — weeks where they
# agree count as exactly zero, which cuts out most of the simulator's noise
python -m data_engine.season_sim --augment --policies production \
       --branch production:your_policy --seeds 42 7 13 --out branch.json

# pool any number of result files into one verdict
python -m data_engine.evaluation bt.json more.json --reference production
```

Seasons can run as separate processes and be pooled afterwards (`--seasons 2025-26 --prior-seasons 2024-25` is one season exactly as `--augment` would run it). A backtest season takes ~6 minutes per seed; a simulator season 20 minutes to 2 hours, because some weeks' solves hit the solver's time limit. The **Season simulation** GitHub Action runs the simulator in the cloud.

---

## Architecture

```
┌──────────────────────────────┐          ┌───────────────────────────┐
│  Local data engine (Python)  │          │   Vercel (free, static)   │
│                              │   JSON   │                           │
│  FPL API ─→ features ─→      │  ──────► │  reads optimized_team.json│
│  XGBoost ─→ PuLP MILP ─→     │          │  ─→ renders the dashboard │
│  optimized_team.json         │          │                           │
└──────────────────────────────┘          └───────────────────────────┘
```

No backend hosting, no database, no paid API. One JSON file is the entire contract between the two halves.

```
var-ified-xi/
├── backend/
│   ├── main.py                      # entrypoint — orchestrates everything
│   ├── config.py                    # every rule, weight and verdict
│   ├── check_deadline.py            # lets the scheduled job exit early
│   ├── wildcard.py                  # is a Wildcard worth it this week, and which squad
│   └── data_engine/
│       ├── fetch_data.py            # FPL API client
│       ├── feature_engineering.py   # rolling form, fixture context
│       ├── historical_data.py       # past seasons for training
│       ├── train_model.py           # the two-stage model
│       ├── optimizer.py             # fresh-squad MILP
│       ├── transfer_optimizer.py    # multi-gameweek transfer MILP
│       ├── planner.py               # the weekly decision — shared by main.py and season_sim
│       ├── rules.py                 # each season's transfer rules (caps, top-ups)
│       ├── entry_data.py            # your real team, from public endpoints
│       ├── rivals.py                # mini-league ownership + chip ledger
│       ├── chips.py                 # chip windows, expiry, double/blank detection
│       ├── injury_log.py            # repeat fitness flags across runs
│       ├── availability_data.py     # pre-deadline injury flags for past seasons
│       ├── horizon_availability.py  # return dates for later weeks (tested, off)
│       ├── backtest.py              # harness 1 — prediction quality
│       ├── season_sim.py            # harness 2 — decision quality
│       └── evaluation.py            # multi-seed verdicts with confidence intervals
│
└── frontend/
    ├── app/                         # pages + layout
    ├── components/                  # PitchView, LeagueView, ThisWeek…
    ├── lib/                         # types, data loading, club kits
    └── public/optimized_team.json   # written by the backend
```

---

## What the dashboard shows

| Section | Answers |
|---|---|
| **This week** | The transfer to make, whether a hit is worth it, who to captain — with the armband as head-to-heads ("Henderson beats Haaland 40%") and the team news for your players |
| **Chip watch** | Every chip you hold placed in its best week up to the chip deadline, with and without a Wildcard now; says "watching, nothing yet" explicitly, so silence never reads as broken |
| **Your league** | What the managers *ahead of you* own, what you're missing, who's already burned which chips |
| **The squad** | The pitch in club colours; tap anyone for their chance of each band of score and fixture run. Each bench player shows how often he'd outscore the starter he'd replace — a "coin flip" between 40% and 60% |
| **The plan** | All six gameweeks of moves this week's decision belongs to |
| **How it works** | The five pipeline stages in plain language |

### Probabilities, chip plan, team news

- **Probabilities.** Every player gets a full points distribution: the model's chance he plays, plus — for the points if he plays — how players projected the same way actually scored across two past seasons. Checked on a season it wasn't fitted on: the likely range holds the real score 85–93% of the time and "chance of 10+" lands within 2 points. Head-to-heads came out overconfident and are recalibrated by one fitted number ([research/2026-10-distributions](backend/research/2026-10-distributions/README.md)).
- **Chip plan** (`chip_planner.py`). Triple Captain, Bench Boost and Free Hit valued in every week to the chip deadline — the captain again, the bench, the best one-week XI your budget buys minus your own — from the squad you'd hold that week, then placed together, one per week. Weeks past the transfer plan's horizon hold its last squad, so they're marked rough.
- **Team news** (`team_news.py`). Within 48 hours of a deadline, the last six days of Google News and BBC Sport headlines for your squad's clubs, this week's buys and the Wildcard squad are read by a free Gemini model, which must cite the headline behind each call. "Out" and "doubt" calls worse than FPL's own flag lower the projection the way an FPL flag would; "rotation" is shown only. It can't be backtested (there are no archived press conferences), so every call is logged with its source and judged live. Needs a `GEMINI_API_KEY` repository secret — free from aistudio.google.com in a project with no billing, so it can't cost anything (the free models can't search the web, which is why the headlines are fetched here). Only calls citing one of those headlines, and a headline that names the player, can change a projection. After every gameweek each call is scored against who actually played (`team_news.judge`, from `data/team_news_calls.json`) and the record is shown with the news; rotation calls can only start moving projections once 30 have been checked at 60%+ right (research/2026-10-team-news). `news-check.yml` runs a one-minute check.

The league view is deliberately **not** an optimizer input. Tilting the solver toward players your rivals don't own was built and tested: it's roughly points-neutral, buying rank variance at the cost of expected points. That's the right trade when you're behind and the wrong one when you're ahead — a judgement about your situation, not one a solver should make quietly for you.

---

## Automation

| Workflow | When | Does |
|---|---|---|
| `weekly.yml` | Every 4 hours | Exits in seconds unless a deadline is within ~30h; otherwise refreshes, retrains, re-solves, commits — triggering a Vercel redeploy |
| `simulate.yml` | Manual | Runs a policy race in the cloud, result table in the run summary |

Set `FPL_TEAM_ID` as a repository variable for transfer plans instead of fresh squads.

**Your Wildcard or Free Hit team.** FPL keeps a chip's transfers private until the deadline, so until then every refresh would plan from last week's squad. Put the team you've set in `backend/overrides.json` under `"team"` (gameweek, chip, bank, the 15 FPL ids in FPL order — XI first, then the bench in substitution order — and the armband). The dashboard then shows that team and lineup, and each refresh re-checks it: a squad change the model would still make (worth 1+ point over the planning window, free until the deadline), or a different XI or captain, appears at the top of *This week*. It's ignored once the deadline passes and FPL's public data catches up.

**Run now.** The dashboard header has a *Run now* button. It starts `weekly.yml` with `force` on — latest FPL data, retrain, re-solve — and reloads the page when the redeployed site has the new numbers, about 6 minutes later. With no setup it reads *Run on GitHub*: it opens the workflow's page, where **Run workflow** starts the run, and the dashboard tab reloads itself when the new deploy lands. For one-tap runs, add a Vercel environment variable `GITHUB_TOKEN`: a fine-grained GitHub token with **Actions: Read and write** on this repository only. The token stays on the server (`app/api/refresh`). Because the site is public, clicks are limited to one run at a time, 10 minutes between manual runs, and 6 a day.

---

## Full documentation

**[📘 Read the project handbook →](docs/HANDBOOK.md)**

Thirteen sections covering the data layer, the train/predict window asymmetry, the two-stage model, both optimizers, the harness trap that voided three tests, the complete evidence ledger, every config knob, and the honest limits.

Also available as a styled standalone page — [`docs/handbook.html`](docs/handbook.html), open it in any browser, no server needed.

---

## Tech stack

| Layer | Tools |
|---|---|
| Data | FPL public API (free, no auth), vaastav archive |
| ML | XGBoost, scikit-learn, pandas |
| Optimization | PuLP (CBC solver) |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |
| Hosting | Vercel + GitHub Actions (free tiers) |

---

## Honest limits

- **It can't manufacture an 80-point week.** Only 2.1% of player-weeks score 10+. What's achievable is moving the *expectation* from ~52 to ~60.
- **Close start/bench calls are close to coin flips.** When two players' projections differ by under a point, the higher one outscores the other only 52–57% of the time in a given week (2024-26, ties left out), and 75% even at a 3-point gap. The edge shows over a season, not in every week.
- **It sees cup, European and international games only through ESPN's public feed** (unofficial; if it breaks, those inputs fall back to neutral values and the dashboard section goes quiet).
- **It can't see team news beyond FPL's own flags.** It reads the injury and suspension flags FPL publishes, not the press conference that hasn't reached them yet.
- **The season simulator is noisy.** The same policy finishes 100–240 points apart on different model seeds, so it can't resolve planner changes much under ~100 points. Most planner verdicts read "no detectable effect" for that reason.
- **An injured or suspended flag is treated as lasting the whole six-week horizon.** (A doubt only counts for the next week.) That looks wrong — about half of suspended players play the following week — but a version using FPL's return dates and measured return curves was built and tested, and it changed only 11 of 222 weekly decisions with no detectable effect. It's in the code, switched off.
- **Neither harness plays chips**, so both totals sit below a real season. They're comparative yardsticks, not predictions.

---

## Disclaimer

Not affiliated with the Premier League, Fantasy Premier League, or the Premier League's official VAR system. Predictions are model estimates, not guarantees — your mini-league rivals have been warned regardless.

---

<div align="center">

Built by [Vatsal](https://github.com/Vatsal-cs) to beat the group chat.

</div>
