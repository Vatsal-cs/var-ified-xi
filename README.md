<div align="center">

# 🟩 VAR-ified XI

**Machine-checked. Math-approved. Your FPL squad, reviewed.**

An AI-driven Fantasy Premier League optimizer that predicts player points with XGBoost and solves for the mathematically optimal squad with a Mixed-Integer Linear Program — then reviews the decision on a live, VAR-inspired dashboard.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![XGBoost](https://img.shields.io/badge/XGBoost-ML-EB1834?style=flat-square)](https://xgboost.ai)
[![PuLP](https://img.shields.io/badge/PuLP-MILP_Solver-2E8B57?style=flat-square)](https://coin-or.github.io/pulp/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org)
[![Tailwind](https://img.shields.io/badge/Tailwind-CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Vercel](https://img.shields.io/badge/Deployed_on-Vercel-black?style=flat-square&logo=vercel)](https://vercel.com)

[Live Demo](https://var-ified-xi.vercel.app) · [Report a Bug](https://github.com/Vatsal-cs/var-ified-xi/issues)

</div>

---

## What this actually does

Most "FPL AI" projects sort players by points-per-million and call it a day. This one doesn't.

VAR-ified XI runs a real decision pipeline:

1. **Prediction** — two XGBoost models, not one. A classifier estimates whether a player will start, come on as a substitute, or not play at all; a second model estimates what he scores *given* he started. Multiplying them separates availability from quality, which is the single biggest source of error in fantasy football. Trained on this season plus the three before it — 87,000 real gameweek results.
2. **Optimization** — a Mixed-Integer Linear Program (PuLP/CBC) that solves for the 15-man squad, the starting XI and the captain across **six gameweeks at once**, under FPL's real constraints: £100.0m budget, 2/5/5/3 quota, valid formation, max 3 per club — and, in transfer mode, one free transfer a week banked to five with −4 per extra.

The result is mathematically provable as optimal *given the model's predictions* — not a heuristic, not a top-N sort.

### Two modes

| | What it answers |
|---|---|
| `python main.py` | "What is the best possible squad?" — for gameweek 1, a wildcard, or a fresh start. |
| `python main.py --team-id 1234567` | "Given the team I actually own, what should I change?" — the useful question in every other gameweek. Reads your public team, works out your bank, sell prices and free transfers, and plans transfers six gameweeks ahead. |

### Everything is backtested

Nothing here ships on intuition. `data_engine/backtest.py` replays whole past seasons gameweek by gameweek — training only on the past, solving a squad, then scoring it against what actually happened, with autosubs and the captain/vice fallback applied. Changes are judged on realized points, and rejected ideas stay in the file as named variants so the evidence is reproducible:

| Change | Verdict |
|---|---|
| Split training populations for the two stages | **+7 pts, MAE 1.16 → 1.05** ✅ |
| Refit on all data after validating | **+127 pts** ✅ |
| Single flat regressor instead of two stages | −53 pts ❌ |
| Position-specific regressors (per OpenFPL) | −104 pts ❌ |

The harness brackets every result between two reference points, so the numbers mean something in absolute terms:

| | points per gameweek (2024-25 / 2025-26) |
|---|---|
| Naive "use each player's last-5 average", no model | 53.4 / 50.8 |
| **This model** | **64.1 / 57.2** |
| Perfect hindsight — unreachable by definition | 148.3 / 155.6 |

So the model is worth roughly **+16% over having no model at all**. (FPL's own published xP looked like an obvious third yardstick, but a squad built from the archived values scores ~99/GW — two thirds of perfect hindsight, which no pre-deadline forecast achieves. Those values are recorded after lineups are known, so the comparison was dropped rather than left in looking authoritative.)

---

## Architecture

```
┌─────────────────────┐         ┌──────────────────────────┐
│   Local Data Engine   │        │      Vercel Frontend      │
│   (runs on your machine)       │   (free tier, static)     │
│                        │        │                          │
│  FPL API → Features    │  JSON  │  Reads optimized_team.json│
│  → XGBoost → PuLP MILP │ ─────► │  → Renders VAR-style      │
│  → optimized_team.json │        │     review dashboard      │
└─────────────────────┘         └──────────────────────────┘
```

No backend hosting, no database, no paid API — the entire system runs on free tiers.

---

## Quickstart

### 1. Clone the repo

```bash
git clone https://github.com/Vatsal-cs/var-ified-xi.git
cd var-ified-xi
```

### 2. Backend — generate a squad

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

This fetches live FPL data, trains the model, solves the optimizer, and writes `optimized_team.json` into both `backend/data/output/` and `frontend/public/`.

### 3. Frontend — view the dashboard

```bash
cd frontend
npm install
npm run dev
```

Open `localhost:3000`.

### 4. Deploy (free)

Push to GitHub → import into [Vercel](https://vercel.com) → set **Root Directory** to `frontend` → deploy. Every `python main.py` + `git push` refreshes the live squad automatically.

---

## How the decision is made

| Stage | What happens |
|---|---|
| **01 · Data Capture** | Pulls every player's gameweek history from FPL's free public API, plus three past seasons from the open [vaastav archive](https://github.com/vaastav/Fantasy-Premier-League) |
| **02 · Feature Model** | Converts raw stats into rolling-form averages over 3/5 gameweek windows — form, xG/xA, BPS, starts, defensive contributions. Training windows are shifted by one gameweek so a row never sees its own match; prediction windows are not, so the coming fixture is judged on the most recent match played |
| **03 · Prediction Engine** | Minutes classifier × conditional points regressor, each trained on the population it needs. Validated on held-out gameweeks, then refit on everything |
| **04 · Constraint Solver** | PuLP MILP over a six-gameweek horizon — squad, XI, captain, and transfers with real free-transfer and hit accounting |
| **05 · Decision** | Writes the confirmed squad and transfer plan to JSON — exactly what the dashboard renders |

The dashboard itself explains all five stages in full, in plain language, with a glossary for the jargon.

---

## Project structure

```
var-ified-xi/
├── backend/                  # Local Python data engine
│   ├── main.py                # Entrypoint — run this
│   ├── config.py               # Rules, paths, constants
│   └── data_engine/
│       ├── fetch_data.py        # FPL API client
│       ├── feature_engineering.py
│       ├── train_model.py       # XGBoost
│       └── optimizer.py         # PuLP MILP
│
└── frontend/                 # Next.js dashboard (Vercel)
    ├── app/                    # Pages + layout
    ├── components/             # PitchView, TransfersPanel, etc.
    ├── lib/                    # Types + data loading
    └── public/optimized_team.json  # Generated by the backend
```

Key backend modules:

| File | Role |
|---|---|
| `data_engine/backtest.py` | Walk-forward season simulator — the arbiter for every change |
| `data_engine/train_model.py` | The two-stage model |
| `data_engine/optimizer.py` | Fresh-squad MILP |
| `data_engine/transfer_optimizer.py` | Multi-gameweek transfer MILP |
| `data_engine/entry_data.py` | Reads your real team from FPL's public endpoints |
| `data_engine/chips.py` | Finds double/blank gameweeks worth a chip |
| `check_deadline.py` | Lets the scheduled job exit early when no deadline is near |

---

## Automation

`.github/workflows/weekly.yml` runs the whole engine twice a day on GitHub's free tier. It checks how far away the next deadline is and exits in seconds unless one is within 30 hours; otherwise it refreshes the data, retrains, re-solves and commits the result — which triggers Vercel to redeploy. Set `FPL_TEAM_ID` as a repository variable to get transfer plans instead of fresh squads.

---

## Tech stack

| Layer | Tools |
|---|---|
| Data | FPL public API (free, no auth) |
| ML | XGBoost, scikit-learn, pandas |
| Optimization | PuLP (CBC solver) |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |
| Hosting | Vercel (free tier) |

---

## Disclaimer

Not affiliated with the Premier League, Fantasy Premier League, or the Premier League's official VAR system. Predictions are model estimates, not guarantees — your mini-league rivals have been warned regardless.

---

<div align="center">

Built by [Vatsal](https://github.com/Vatsal-cs) to beat the group chat.

</div>
