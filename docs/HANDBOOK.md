# VAR-ified XI — Project Handbook

> Everything the system does, why each piece is built the way it is, and what the
> evidence actually says — including the parts where the evidence said no.
>
> A styled, standalone version of this document is at
> [`docs/handbook.html`](handbook.html) — open it in any browser.

**Contents**

1. [The core idea](#1--the-core-idea)
2. [The pipeline, end to end](#2--the-pipeline-end-to-end)
3. [Data layer](#3--data-layer)
4. [Feature engineering](#4--feature-engineering)
5. [The model](#5--the-model)
6. [The optimizers](#6--the-optimizers)
7. [How things get tested](#7--how-things-get-tested)
8. [The evidence ledger](#8--the-evidence-ledger)
9. [Running it](#9--running-it)
10. [Every knob in config.py](#10--every-knob-in-configpy)
11. [The dashboard](#11--the-dashboard)
12. [Automation](#12--automation)
13. [Limits and open questions](#13--limits-and-open-questions)

---

## 1 · The core idea

Fantasy Premier League is two problems wearing one coat, and almost every tool
conflates them.

The first is **prediction**: how many points will this player score next week?
The second is **decision**: given what I already own, my bank, my free transfers
and the rules, what should I actually do? A perfect predictor paired with a bad
decision rule loses to a mediocre predictor paired with a good one, because the
decision rule is what touches your team.

This project treats them as separate systems with separate evidence. There is a
model, and there is a solver, and each has its own test harness that the other
cannot flatter.

### The one rule that governs everything

> No change ships on intuition. A change ships when it scores more *realized*
> points across **every** season tested. Not better accuracy, not a
> nicer-sounding rationale — points, in every season, or it stays off.
>
> Ideas that lose are kept in the codebase as named, re-runnable variants with
> their exact numbers, so a rejected idea can never quietly return as a fresh
> insight.

### Why "realized points" and not accuracy

Mean absolute error measures how close predictions land on average across ~600
players. But you only field 15, and the armband doubles one of them. A model can
shave its MAE by getting the vast irrelevant middle of the player pool slightly
righter while getting your captain wrong.

The only number that reflects what you'd have scored is the one the harness
computes: build the squad, then score it against what actually happened,
autosubs and captain fallback included.

---

## 2 · The pipeline, end to end

One command runs all of this. `backend/main.py` is the orchestrator and reads
top to bottom as the list below.

| # | Stage | What happens | File |
|---|---|---|---|
| 1 | **Fetch** | Bootstrap (players, teams, fixtures), fixture list, and every player's match history — ~660 API calls, politely spaced. Cached to disk per day | `fetch_data.py` |
| 2 | **Build features** | Flatten histories into one row per player per gameweek, attach rolling-form averages over 3/5 game windows, fixture context, player context. 36 columns reach the model | `feature_engineering.py` |
| 3 | **Augment** | Three past seasons from the open vaastav archive — ~87,000 extra training rows, built through identical feature code so distributions match | `historical_data.py` |
| 4 | **Train & predict** | Two XGBoost models: will he play, and what does he score if he does. Validated on held-out gameweeks, then refit on everything. Predicts each player against each of the next six fixtures | `train_model.py` |
| 5 | **Solve** | Either a fresh 15-man squad, or a transfer plan from the squad you actually own, across six gameweeks with real transfer accounting | `optimizer.py`, `transfer_optimizer.py` |
| 6 | **Enrich** | Scan the calendar for double/blank gameweeks worth a chip; pull your mini-league's ownership and chip ledger | `chips.py`, `rivals.py` |
| 7 | **Write JSON** | One file, to `backend/data/output/` and `frontend/public/` | `optimized_team.json` |

**There is no server.** The frontend is a static Next.js site that reads a JSON
file committed to the repo. No database, no API layer, no hosting bill.
Refreshing the squad is a file write plus a git push.

---

## 3 · Data layer

### Where everything comes from

| Source | Gives | Auth |
|---|---|---|
| `fantasy.premierleague.com/api` | Live players, prices, fixtures, per-player history, your team, your leagues | None |
| `vaastav/Fantasy-Premier-League` | Three completed seasons of per-gameweek results | None |
| `olbauday/FPL-Core-Insights` | Per-gameweek set-piece order, ClubElo. Wired up, currently off | None |
| `football-data.co.uk` | Historical closing odds. Wired up, tested, rejected | None |

### The endpoints your team comes from

Transfer-plan mode reads your real squad **without ever logging in**:

```
entry/{id}/                      name, bank, squad value, leagues
entry/{id}/history/              gameweek scores, transfers used, chips played
entry/{id}/transfers/            every transfer, with the price paid
entry/{id}/event/{gw}/picks/     the 15 you fielded, and who was captain
leagues-classic/{id}/standings/  your mini-league table
```

From these the system reconstructs three things FPL does *not* publish directly:
how many free transfers you have, what each player would sell for, and which
chips every rival has burned.

### Sell price, exactly as FPL computes it

You keep only half of any price rise, rounded down to the nearest £0.1m. Since
prices are stored in tenths, that is integer division:

```python
if current <= purchase:  sell = current
else:                    sell = purchase + (current - purchase) // 2
```

### Free transfers, reconstructed

You earn one per gameweek and may hold **at most two**. Wildcard and Free Hit
weeks don't consume them. The count is rebuilt by replaying your history
forward.

> This cap was wrong for a while — set to 5, a rule from an earlier season — and
> produced plans spending transfers you didn't have.

### ⚠ A real bug worth knowing about

Once a gameweek kicks off, FPL's API **pre-creates zero-filled history rows** for
matches that haven't been played yet. Run the pipeline mid-gameweek without
filtering and every player with a later kickoff looks like he was just benched
for a duck — which halves his play probability and throws every premium out of
the squad.

**The fix:** keep only rows whose fixture is actually finished.

---

## 4 · Feature engineering

36 columns reach the model, in six families. Every one is produced identically
for live data and for the historical archive — that symmetry is what lets three
past seasons be used as training data at all.

| Family | Columns | Captures |
|---|---|---|
| **Form** | minutes, points, ict, influence, creativity, threat (3 & 5 game) | Recent output |
| **Underlying** | xg, xa, xgi, xgc | Chance quality — more forward-looking than points, which are partly luck |
| **Bonus** | bps_avg, bonus_avg | Bonus is ~10% of all scoring and highly persistent |
| **Rotation** | starts_avg_3, starts_avg_5 | Started-or-not is sharper than minutes: 45' off the bench and 45' before a red card look identical otherwise |
| **Defensive** | dc_avg, saves_avg, cs_avg, gc_avg | Defensive Contribution points, clean sheets, saves |
| **Context** | was_home, team/opp strength, difficulty, cost, ownership, position, rest days, age | The fixture and the player's standing |

### 🔑 The most important idea in this file

**Training windows are shifted by one gameweek. Prediction windows are not.**

It looks like a bug. It is the opposite.

- A **training** row for gameweek *t* must average matches *t-3…t-1*. If it
  included *t* itself, the model would be shown the answer inside the question
  and would learn nothing useful.
- A **prediction** row is the opposite case: the match hasn't been played yet, so
  the most recent completed match is legitimate input, not leakage. Shifting it
  away would mean every prediction is made on week-old form — and in the opening
  weeks of a season, shifting away the only gameweek played leaves every feature
  at zero.

Both paths produce the same semantics: *the w matches immediately before the
fixture being predicted*.

### Deliberately absent

Two things that sound like obvious features are not features, on purpose:

- **Injury-flag history** — we don't have it retroactively for past gameweeks, so
  training on it would create a train/predict mismatch. It's applied as a
  prediction-time multiplier instead.
- **FPL's own expected points** (`ep_next`) — the archived values are recorded
  *after* lineups are known. A squad built from them scores ~99 points a gameweek
  against ~148 for perfect hindsight, which no pre-deadline forecast achieves. It
  is contaminated and **must not be reinstated**.

---

## 5 · The model

Rotation risk is the single biggest source of error in fantasy football, and a
flat points regressor smears it together with quality. A player projected at 2.0
might be a certain starter who is mediocre, or a brilliant player who might not
play. Those demand opposite decisions.

### Two stages

```
Stage 1 — MINUTES CLASSIFIER  (XGBoost, 3-class)
          P(didn't play) · P(cameo, 1-59') · P(full, 60'+)

Stage 2 — CONDITIONAL POINTS  (XGBoost regressor)
          E[points | played 60+ minutes]

          xP = P(full) × E[pts|full] + P(cameo) × cameo_average[position]
```

### The split that mattered most

The two stages train on **different populations**, and getting this right was the
largest single accuracy gain in the project:

- The **classifier** trains on *every* row. It has to see non-players to learn
  what a non-player looks like.
- The **regressor** trains only on *established starters*. It's learning pure
  quality, and feeding it rows from players who barely feature teaches it to
  under-predict everyone.

Training both on the filtered set — the original design — cost 7 points and
pushed MAE from 1.05 to 1.16.

### Refit after validating

Accuracy is measured on a time-based holdout: the most recent 5 gameweeks, never
seen during training. Then the model is **retrained on everything, holdout
included**, before going into the weekend.

Worth **+127 points** — the most recent gameweeks are the most informative ones,
and throwing them away to preserve a clean test set is a mistake you pay for
every single week.

### Prediction-time adjustments

Applied after the model, never learned by it:

| Adjustment | Effect |
|---|---|
| FPL's `chance_of_playing` | Scales the play probability — the correct place for it in a decomposed model |
| Hard status (injured/suspended) | Floors the projection to 10% |
| Repeat fitness flags (3+ this season) | ×0.85 caution multiplier, from a log that persists across runs |
| No fixture that gameweek | Zero — a genuine blank |

---

## 6 · The optimizers

Both are Mixed-Integer Linear Programs solved with PuLP/CBC. A MILP gives you
something a "sort by points-per-million" heuristic never can: the answer is
*provably optimal* given the predictions, under every constraint simultaneously.

### The hard rules, encoded

| Rule | Value |
|---|---|
| Budget | £100.0m |
| Squad | 15 — exactly 2 GK / 5 DEF / 5 MID / 3 FWD |
| Starting XI | 1 GK, 3–5 DEF, 2–5 MID, 1–3 FWD |
| Max per club | 3 |
| Free transfers | 1 per week, hold at most 2 |
| Extra transfer | −4 points |

### Why six gameweeks, not one

A one-week solver will happily sell a player to chase a single good fixture, then
have to buy him straight back. Planning six weeks at once sees that and declines
— and it can deliberately bank a transfer this week to afford two next week, a
move no greedy weekly optimizer can find.

Future weeks are discounted at **0.85 per gameweek**: a projection five weeks out
is a weaker claim than one for Saturday, and you'll get to revise it before then
anyway.

### The objective function

```
maximise   Σ over gameweeks t, discounted by 0.85^t of:

             xP(starters)                    the XI
           + xP(captain)                     doubled, so counted twice
           + 0.12 × xP(bench)                autosub insurance
           − (4 + HIT_MARGIN) × hits         see below
```

### ✅ The single biggest win in the project

A hit costs 4 points. So the naive rule is "take it if the gain beats 4". That's
wrong, because **the gain is a *projection* and the loss is a *certainty***.
`HIT_MARGIN` is the extra the move must clear before it's worth that asymmetry.

At the old margin of 2 (hits needing to gain 6), the planner spent **228 points
on 57 hits across two seasons and still finished behind a version banned from
taking any**. At a margin of 4 (hits needing to gain 8) it wins both seasons by
+154 and +145 — **+299 pooled, about 4 points a gameweek**.

### The candidate pool

Six gameweeks × 660 players × five binary decisions each is a problem CBC will
chew on for a very long time to tell you the 400th-best midfielder isn't going in
your squad. The pool is trimmed to the best 20 GK / 55 DEF / 60 MID / 35 FWD by
horizon value, *plus everyone you already own* (so they can always be sold). This
turns a multi-hour solve into seconds and costs nothing real.

### The hit recommendation, and a bug worth understanding

The dashboard answers "is a hit worth it this week?" The first implementation
solved two independent plans — one banned from hits, one unconstrained — and
*diffed* their transfers.

That's wrong: two independently optimal solutions can land on entirely unrelated
squads, so the "difference" was meaningless and reported nonsense like an −8 hit
when only −4 was possible.

It now solves **sequentially**: solve the free plan, build a synthetic team state
representing "you, having just made those moves" (resulting squad, resulting
bank, sell prices updated so newly bought players sell for exactly what you
paid), then re-solve from there. The second solve's transfers *are* the extra
moves a hit buys. No diffing.

---

## 7 · How things get tested

There are two harnesses because there are two problems. Using one to judge the
other is how you end up confidently shipping something harmful.

| | `backtest.py` | `season_sim.py` |
|---|---|---|
| **Answers** | Are the predictions good? | Are the decisions good? |
| **Squad** | Rebuilt from scratch every week, unlimited transfers | One squad carried forward all season |
| **Transfers** | Free and unlimited | 1/week, hold 2, −4 per extra |
| **Prices** | As they were | Move, with half-the-rise selling |
| **Use for** | Model and feature changes | Anything in the transfer planner |
| **Score** | ~4600 / 2 seasons | ~4200 / 2 seasons |

Both replay seasons gameweek by gameweek, training *only* on data strictly before
the week being predicted, then score the chosen team against what actually
happened — including autosubs and the captain-to-vice fallback exactly as FPL
applies them.

### Two reference points that make the numbers mean something

| Benchmark | Points per gameweek (2024-25 / 2025-26) |
|---|---|
| `naive_form` — no model, just each player's last-5 average | 53.4 / 50.8 |
| **This model** | **64.1 / 57.2** |
| `hindsight` — optimise on what actually happened | 148.3 / 155.6 |

So the model is worth roughly **+16% over having no model at all**. The hindsight
ceiling exists to stop anyone mistaking a good score for a great one.

### 🔑 How season_sim keeps the comparison honest

**One model, many policies.** The model trains once per gameweek and every policy
is handed the identical predictions. So any difference in final score is caused
by the decision rule and nothing else — and it runs far faster than racing whole
pipelines.

**Form is frozen at the deadline; fixtures are not.** Rolling form comes only from
matches played before the gameweek being planned. But fixture context — home or
away, opponent, rest days — is taken from the real calendar, because in life the
fixture list is published months ahead. That distinction is where most season
simulators quietly leak.

### ⚠ The trap that voided three tests

A variant that changes how rows are *built* — an optional feature join — must
have its flag active **while the data loads**, not just around fit and predict.
`backtest.py` used to load every season once up front and only afterwards enter
the variant's context, so such variants trained on neutral constant columns and
reported a verdict on nothing.

`Variant.context` now stays open across data loading, and frames are rebuilt per
variant. The same class of bug hit a captain flag that never reached the solver,
producing byte-identical results that were reported as "no difference" when the
truth was "never ran".

**Always verify a knob binds before trusting its verdict.** For set-pieces that
meant checking 0 of 29,757 rows carried a duty with the flag off, and 1,664 with
it on.

---

## 8 · The evidence ledger

Every idea ever tested, with its number. This table is the project's memory — it
exists so nobody, including future you, re-proposes something already disproved.

### Accepted

| Change | Effect | Why |
|---|---:|---|
| Hit must gain 8, not 6 | **+299** | Won both seasons. Old setting spent 228 points on hits and lost to taking none |
| Refit on all data after validating | **+127** | Recent gameweeks are the most informative |
| Split training populations | **+7**, MAE 1.16→1.05 | Classifier needs non-players; regressor doesn't |
| Backtest from GW2, not GW8 | — | The early-season regime was never being tested |

### Rejected

| Idea | Effect | Why it failed |
|---|---:|---|
| Per-position regressors | −104 | Splits the feature set too thin |
| Captain on ceiling, not mean | −75 | Chasing upside drags high-variance players into the whole squad; the squad lost more than the armband gained |
| Set-piece / penalty features | −62 | Takers are just good players — their penalty income is already in their xG and points history. MAE identical to 3 decimals |
| Recency weighting by season | −58 | Lost both seasons |
| Single flat regressor | −53 | Smears rotation risk into quality |
| Betting-odds features | −32 | Model *does* use them (~11% of gain) and still scores worse — the signal is already in rolling xG and team strength |
| Early-season shrinkage | −64 | Multi-season training already covers the thin-history weeks |
| Free-transfer margin | split | Looked like +96 pooled; was −10 / +106 by season. Also stops binding once hits are priced right |
| Differential tilt | ≈0 | Roughly points-neutral once measured fairly. Buys rank variance — the right trade only when behind |

> **Nine of thirteen ideas failed.** That ratio is the point, not an
> embarrassment: every one of them sounded right beforehand, and without the
> harness most would have shipped.

---

## 9 · Running it

### First time

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Generate a squad

```bash
# "What is the best possible squad?" — GW1, or a wildcard
python main.py

# "Given the team I own, what should I change?" — every other week
python main.py --team-id 9927826
```

Takes 5–15 minutes, most of it fetching ~660 player histories one at a time.
Writes `optimized_team.json` to two places.

### View the dashboard

```bash
cd frontend
npm install
npm run dev      # localhost:3000
```

### Test a model change

```bash
python -m data_engine.backtest --seasons 2024-25 2025-26 \
       --variants production your_new_variant --augment

# faster while iterating — every 3rd gameweek
python -m data_engine.backtest --seasons 2025-26 --stride 3
```

### Test a transfer-planner change

```bash
python -m data_engine.season_sim --seasons 2025-26 2024-25 \
       --policies baseline hit_margin_4 no_hits
```

Prints a table per season and then the pooled total. **A change has to win every
season** — the per-season split exists precisely because one strong season can
carry a harmful change into looking like an improvement.

> **Long runs:** a full two-season, six-policy race takes hours. Push it to
> GitHub Actions rather than tying up your laptop — the **Season simulation**
> workflow runs it in the cloud and writes the result table straight into the run
> summary, readable from a phone.

---

## 10 · Every knob in config.py

Each carries an inline comment with its verdict and the exact numbers behind it.
**Changing any of them without re-running a harness undoes evidence.**

| Setting | Value | Meaning |
|---|---:|---|
| `HORIZON_GWS` | 6 | Gameweeks planned at once |
| `HORIZON_DECAY` | 0.85 | Discount per week into the future |
| `HIT_MARGIN` | 4.0 | A hit must gain 4+4=8. **The big win** |
| `FREE_TRANSFER_MARGIN` | 0.0 | Free transfers cost nothing. Tested at 1.5 — a split |
| `DIFFERENTIAL_WEIGHT` | 0.0 | Tilt toward unowned players. Points-neutral; situational |
| `MAX_FREE_TRANSFERS` | 2 | Real cap. Was wrongly 5 |
| `BENCH_WEIGHT` | 0.12 | Autosub insurance value |
| `CAPTAIN_QUANTILE` | 0.80 | Ceiling model's quantile. Built, rejected twice, kept off |
| `VALIDATION_HOLDOUT_GAMEWEEKS` | 5 | Time-based holdout size |
| `SOLVER_TIME_LIMIT` | 120s | Near-optimal before the deadline beats perfect after it |
| `ATTACH_ODDS` | False | Rejected −32 |
| `ATTACH_SETPIECE` | False | Rejected −62 |
| `RECENCY_SEASON_DECAY` | 1.0 | Disabled — rejected −58 |
| `FORM_SHRINKAGE_GAMES` | 0.0 | Disabled — rejected −64 |

---

## 11 · The dashboard

A static Next.js 16 site whose entire data source is one JSON file. Its job is to
make a decision legible, not to look like a dashboard — so it leads with the
single move that's due and puts the reasoning underneath.

| Section | Answers |
|---|---|
| **This week** | The transfer to make, whether a hit is worth it, who to captain |
| **Chip watch** | When to play a chip — and explicitly says "watching, nothing yet" so silence never reads as broken |
| **Your league** | What the managers ahead of you own, what you're missing, who's burned which chips |
| **The squad** | The pitch, in club colours. Tap anyone for their projection and fixture run |
| **The plan** | All six gameweeks of moves this week's decision belongs to |
| **How / FAQ** | The five pipeline stages, in plain language |

### Why the league view is not an optimizer input

It would be easy to make the solver chase players your rivals don't own. It was
built and tested, and it's roughly points-neutral: it buys rank variance at the
cost of expected points.

That's the right trade when you're behind and need to catch someone, and the
wrong one when you're ahead protecting a lead. That's a judgement about *your
situation*, not something a solver should make quietly on your behalf. So the
numbers go on the page and the call stays yours.

---

## 12 · Automation

| Workflow | When | Does |
|---|---|---|
| `weekly.yml` | Twice daily (cron) | Checks the next deadline and exits in seconds unless one is within ~30h. Otherwise refreshes, retrains, re-solves, commits — which triggers a Vercel redeploy |
| `simulate.yml` | Manual | Runs a policy race in the cloud and writes the result table into the run summary |

Set `FPL_TEAM_ID` as a repository variable to get transfer plans rather than
fresh squads. Public repo means unlimited free Actions minutes.

> **If a deploy fails:** check whether the commit touched `frontend/` at all. If
> it didn't, suspect Vercel's build cache — redeploy with *Use existing Build
> Cache* unticked. A stale Turbopack cache produced font-resolution errors on a
> commit that changed only Python files.

---

## 13 · Limits and open questions

### What this genuinely cannot do

- **It can't manufacture an 80-point week.** Only 2.1% of player-weeks score 10+;
  0.3% score 15+. An 80-point week needs a captain haul plus two or three others
  landing at once. What's achievable is moving the *expectation* from roughly 52
  to roughly 60.
- **It can't see team news.** The simulation reacts to a player having stopped
  playing, not to the press conference saying he will.
- **Neither harness plays chips.** Both totals sit below a real chip-using season.
  They're comparative yardsticks, not season predictions.
- **Predictions are conditional means on a violently skewed distribution.** Among
  players who start, real scores spread 3.16 points; predictions spread 1.28.
  That compression is mathematically correct and is why expected points alone
  will never identify who's about to haul.

### Genuinely open

- **Newly appointed set-piece takers.** The duty itself adds nothing — but a
  player who just *inherited* penalties has a history that can't show it yet.
  That needs a change-detection feature (duty this week he didn't have last
  week), not the duty. Data and join are already in place.
- **The odds re-test reproduced the old numbers exactly** despite the data
  demonstrably differing. The verdict is settled; the coincidence isn't
  explained.
- **A decoupled captain test** — pick the squad on the mean, then the captain on
  ceiling — was never run. It would separate the two effects the rejected test
  conflated.

### 🔑 If you change one thing, change this

Keep the rule. Every knob in `config.py` carries its verdict because the
alternative is folklore — a codebase full of settings nobody remembers the reason
for. When you test something new, write the number down next to the setting,
whichever way it goes.

---

*Compiled September 2026. Evidence: walk-forward backtests over 2024-25 and
2025-26, transfer-constrained season simulation, live FPL API. Not affiliated
with the Premier League or Fantasy Premier League.*
