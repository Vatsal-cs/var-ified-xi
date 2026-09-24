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

Trained on this season plus three past ones — about 87,000 real gameweek results.

### 2 · Decision — a solver, not a heuristic

A PuLP/CBC Mixed-Integer Linear Program solves the 15-man squad, the starting XI, the captain and the transfers across **six gameweeks at once**, under every real constraint: £100.0m budget, 2/5/5/3 quota, legal formation, max 3 per club, one free transfer a week (hold at most two), −4 per extra.

The answer is *provably optimal given the predictions*. Not a top-N sort.

### Two modes

| Command | Answers |
|---|---|
| `python main.py` | "What's the best possible squad?" — GW1, a wildcard, a fresh start |
| `python main.py --team-id 1234567` | "Given the team I own, what should I change?" — every other week. Reads your public team, works out your bank, sell prices and free transfers, plans six gameweeks ahead |

---

## Nothing ships on intuition

A change ships when it scores more **realized** points across **every** season tested. Not better accuracy — points, in every season, or it stays off.

Ideas that lose stay in the codebase as named, re-runnable variants with their exact numbers, so a rejected idea can never quietly return as a fresh insight.

**Nine of thirteen ideas failed.** That ratio is the point — every one of them sounded right beforehand.

| Change | Verdict | |
|---|---:|---|
| Hit must gain 8, not 6 | **+299** | ✅ biggest win — ~4 pts/gameweek |
| Refit on all data after validating | **+127** | ✅ |
| Split training populations for the two stages | **+7**, MAE 1.16 → 1.05 | ✅ |
| Per-position regressors | −104 | ❌ splits the feature set too thin |
| Captain on ceiling instead of mean | −75 | ❌ upside-chasing infects the whole squad |
| Set-piece / penalty features | −62 | ❌ takers are just good players; already in their xG |
| Recency weighting by season | −58 | ❌ lost both seasons |
| Single flat regressor | −53 | ❌ smears rotation risk into quality |
| Betting-odds features | −32 | ❌ model uses them and still scores worse |
| Differential tilt toward unowned players | ≈0 | ❌ points-neutral; buys rank variance only |

### The one that mattered most

At the old setting, a points hit only had to gain 6. Across two seasons the planner **spent 228 points on 57 hits and still finished behind a version banned from taking any**. Requiring 8 wins both seasons — +154 and +145, **+299 pooled**.

The gain is a *projection*; the −4 is a *certainty*. That asymmetry has to be priced.

### Bracketed so the numbers mean something

| | points per gameweek (2024-25 / 2025-26) |
|---|---|
| `naive_form` — no model, just each player's last-5 average | 53.4 / 50.8 |
| **This model** | **64.1 / 57.2** |
| `hindsight` — optimise on what actually happened, unreachable | 148.3 / 155.6 |

Roughly **+16% over having no model at all**.

> FPL's own published xP looked like an obvious third yardstick, but a squad built from the archived values scores ~99/GW — two thirds of perfect hindsight, which no pre-deadline forecast achieves. Those values are recorded after lineups are known. The comparison was dropped rather than left in looking authoritative.

---

## Two harnesses, two questions

| | `backtest.py` | `season_sim.py` |
|---|---|---|
| **Answers** | Are the *predictions* good? | Are the *decisions* good? |
| **Squad** | Rebuilt from scratch weekly, unlimited transfers | One squad carried forward all season |
| **Transfers** | Free and unlimited | 1/week, hold 2, −4 per extra |
| **Prices** | As they were | Move, with half-the-rise selling |
| **Use for** | Model and feature changes | Anything in the transfer planner |

Both replay seasons gameweek by gameweek, training only on data strictly before the week being predicted, then score the chosen team against what actually happened — autosubs and captain-to-vice fallback included.

`season_sim.py` trains **one model per gameweek and hands the identical predictions to every policy**, so any difference in score is caused by the decision rule and nothing else. Form is frozen at the deadline; fixture context is not, because the fixture list really is published months ahead.

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
# model / feature changes
python -m data_engine.backtest --seasons 2024-25 2025-26 \
       --variants production your_variant --augment

# transfer-planner changes
python -m data_engine.season_sim --seasons 2025-26 2024-25 \
       --policies baseline hit_margin_4 no_hits
```

A full race takes hours — the **Season simulation** GitHub Action runs it in the cloud and writes the result table into the run summary.

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
│   └── data_engine/
│       ├── fetch_data.py            # FPL API client
│       ├── feature_engineering.py   # rolling form, fixture context
│       ├── historical_data.py       # past seasons for training
│       ├── train_model.py           # the two-stage model
│       ├── optimizer.py             # fresh-squad MILP
│       ├── transfer_optimizer.py    # multi-gameweek transfer MILP
│       ├── entry_data.py            # your real team, from public endpoints
│       ├── rivals.py                # mini-league ownership + chip ledger
│       ├── chips.py                 # double/blank gameweek detection
│       ├── injury_log.py            # repeat fitness flags across runs
│       ├── backtest.py              # harness 1 — prediction quality
│       └── season_sim.py            # harness 2 — decision quality
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
| **This week** | The transfer to make, whether a hit is worth it, who to captain |
| **Chip watch** | When to play a chip — and says "watching, nothing yet" explicitly, so silence never reads as broken |
| **Your league** | What the managers *ahead of you* own, what you're missing, who's already burned which chips |
| **The squad** | The pitch in club colours; tap anyone for their projection and fixture run |
| **The plan** | All six gameweeks of moves this week's decision belongs to |
| **How it works** | The five pipeline stages in plain language |

The league view is deliberately **not** an optimizer input. Tilting the solver toward players your rivals don't own was built and tested: it's roughly points-neutral, buying rank variance at the cost of expected points. That's the right trade when you're behind and the wrong one when you're ahead — a judgement about your situation, not one a solver should make quietly for you.

---

## Automation

| Workflow | When | Does |
|---|---|---|
| `weekly.yml` | Twice daily | Exits in seconds unless a deadline is within ~30h; otherwise refreshes, retrains, re-solves, commits — triggering a Vercel redeploy |
| `simulate.yml` | Manual | Runs a policy race in the cloud, result table in the run summary |

Set `FPL_TEAM_ID` as a repository variable for transfer plans instead of fresh squads.

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
- **It can't see team news.** It reacts to a player having stopped playing, not to the press conference saying he will.
- **Neither harness plays chips**, so both totals sit below a real season. They're comparative yardsticks, not predictions.

---

## Disclaimer

Not affiliated with the Premier League, Fantasy Premier League, or the Premier League's official VAR system. Predictions are model estimates, not guarantees — your mini-league rivals have been warned regardless.

---

<div align="center">

Built by [Vatsal](https://github.com/Vatsal-cs) to beat the group chat.

</div>
