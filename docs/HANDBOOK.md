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
> points than production — by more than the noise — in **every** season tested,
> and keeps that sign on seasons that were never used to choose it.
>
> Ideas that lose are kept in the codebase as named, re-runnable variants with
> their exact numbers, so a rejected idea can never quietly return as a fresh
> insight.

#### How the noise is measured, and why it changed the rule

Re-running production with nothing changed but XGBoost's random seed moves the
two-season backtest by up to **175 points** (4,443 to 4,618), with MAE and rank
correlation identical to three decimals: the solver turns tiny prediction
differences into different squads. In half of all seed pairs, one seed "won both
seasons" — so the original rule (one run, more points in every season) passed a
change that does nothing about half the time.

Since October 2026 every comparison runs on several seeds (`--seeds`), and
`evaluation.py` decides it from per-gameweek differences averaged over seeds,
with a block-bootstrap 95% interval:

| Verdict | Rule, written down before the run |
|---|---|
| **better** | pooled interval above zero *and* ahead in every season |
| **worse** | pooled interval below zero *and* behind in every season |
| **no detectable effect** | anything else. The harness can't tell — not "rejected" |

Changes are chosen on **2024-25 and 2025-26**. **2022-23 and 2023-24** are held
back and run *once* per change that comes out "better", with the acceptance
criterion written down first. The live 2026-27 season is the final holdout.

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
| `olbauday/FPL-Core-Insights` | FPL's player payload snapshotted after every gameweek (2024-25 on): the injury flags a manager saw before each deadline, for the harnesses; set-piece order (wired up, off) | None |
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

You earn one per gameweek and may bank **up to five**; a team's first gameweek is a free squad pick and banks nothing. Wildcard and Free Hit
weeks don't consume them. The count is rebuilt by replaying your history
forward.

> This cap was wrongly set to 2 for a while. A real team showing two free
> transfers at GW5 was taken as proof — but that team was created at GW2, and
> the creation week banks nothing, so a cap of five produces the same count.
> The official rules (and the live API's `max_extra_free_transfers = 4`) say five.

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

Measured at **+127 points** on one seed. Re-measured on five seeds per season in
October 2026 it is **+43** (95% CI [−75, +171]) — ahead in both seasons and in
8 of 10 seed-seasons, but inside the noise, so: no detectable effect. It stays;
it costs nothing and points the right way, but +127 overstated it.

### Five models, averaged

A single model's picks partly depend on its random seed: retraining with only
the seed changed moves a two-season backtest by up to 175 points, with
accuracy identical. So production trains **five copies** (seeds 42, 42+7919,
…) and averages their projections and play probabilities, before the
availability adjustments are applied.

Pre-registered as "steadier picks at no cost" and tested on all four seasons:
the starting XI two independently-trained versions share rose from 75–78% to
86–88%, captain agreement from 70–81% to 81–89%, accuracy improved slightly
everywhere, and points were not worse (+25 [−37, +92] on the tuning seasons,
+23 [−34, +82] held back). It costs four extra model fits — about a minute.

It does **not** steady the moves planned for later weeks: on the live team,
independent runs matched on them only about 1 time in 10, single model or
averaged. Those weeks are near-ties between similar options. This week's move
was unanimous across 12 independent models.

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
| Free transfers | 1 per week, bank up to 5 |
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

### What happened to "the single biggest win"

A hit costs 4 points, and the gain is a *projection* while the loss is a
*certainty*. `HIT_MARGIN` is the extra a move must clear on top of the 4.

This used to be the project's headline: at a margin of 2 the planner spent 228
points on 57 hits and finished behind a version that took none, and a margin of
4 won both seasons by **+299 pooled**. The October 2026 audit found that number
measured a different game. The simulator banked at most 2 free transfers in
seasons that allowed 5, let the solver plan and take hits in any week (production
only ever *advises* a hit this week), and leaked future prices into its
multi-week projections.

Re-measured with all of that fixed — the shipping procedure, each season's real
rules, 3 seeds per season:

| Hit check margin (vs 4) | 2024-25 | 2025-26 | Pooled, 95% CI |
|---|---:|---:|---|
| 0 — any hit that gains more than 4 | −82 | +13 | −69 [−186, +48] |
| 2 | −43 | +44 | +1 [−97, +92] |
| 6 | +54 | −7 | +47 [−64, +155] |
| never take a hit | +62 | −19 | +44 [−95, +196] |

**No detectable effect, every setting.** The direction flips between seasons.
The margin stays at 4 because nothing beat it, not because 4 is proven.

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

The whole weekly decision — free-transfer plan, hit check, then captain and vice
on the two highest projections in the XI — lives in `planner.py`. `main.py` calls
it for your recommendation and `season_sim.py` calls the same function to
measure it, so the harness can't drift from what ships.

---

## 7 · How things get tested

There are two harnesses because there are two problems. Using one to judge the
other is how you end up confidently shipping something harmful.

| | `backtest.py` | `season_sim.py` |
|---|---|---|
| **Answers** | Are the predictions good? | Are the decisions good? |
| **Squad** | Rebuilt from scratch every week, unlimited transfers | One squad carried forward all season |
| **Transfers** | Free and unlimited | That season's real rules (`rules.py`), −4 per extra |
| **Prices** | As they were | Move, with half-the-rise selling |
| **Injury flags** | As published before each deadline (from 2024-25) | Same, trimmed exactly as production trims them |
| **Use for** | Model and feature changes | Anything in the transfer planner |
| **Score** | ~4,670 / 2 seasons | ~4,160 / 2 seasons |

Both replay seasons gameweek by gameweek, training *only* on data strictly before
the week being predicted, then score the chosen team against what actually
happened — including autosubs and the captain-to-vice fallback exactly as FPL
applies them.

### Two reference points that make the numbers mean something

| Benchmark | Points per gameweek (2024-25 / 2025-26) |
|---|---|
| `naive_form` — no model, just each player's last-5 average | 57.7 / 51.9 |
| **This model** (mean of 5 seeds) | **64.6 / 61.7** |
| `hindsight` — optimise on what actually happened | 149.0 / 154.6 |

So the model is worth roughly **+15% over having no model at all** (−614 points
for no model, 95% CI [−876, −361] — the clearest result in the project). The
hindsight ceiling exists to stop anyone mistaking a good score for a great one.

> These are the October 2026 numbers. Before the audit the table read 53.6 /
> 51.6 for no model and 63.2 / 61.6 for the model ("+19%"). Both rose because
> double-gameweek players are now predicted for both matches; the naive
> forecast gained more from that, so the model's margin narrowed.

### 🔑 How season_sim keeps the comparison honest

**One model, many policies.** The model trains once per gameweek and every policy
is handed the identical predictions. So any difference in final score is caused
by the decision rule and nothing else — and it runs far faster than racing whole
pipelines.

**The same decision code.** The simulator calls `planner.plan_week` — the
function `main.py` calls to make your recommendation — so what it measures is
what the dashboard tells you to do. Before October 2026 it ran its own
procedure, which production never did.

**Form, price and injury news are frozen at the deadline; fixtures are not.**
Rolling form comes only from matches played before the gameweek being planned,
and every week of the horizon carries the deadline's price and flags. But
fixture context — home or away, opponent, rest days — is taken from the real
calendar, because in life the fixture list is published months ahead. Price was
the leak: it is the model's most important feature, and it used to be read from
each future week's row.

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

Every verdict here was first decided on **one seed**. In October 2026 the
biggest claims were re-run on the corrected harness — 5 seeds per season in the
backtest, 3 in the simulator — under the verdict rules in section 1.

### Re-measured

| Claim | First (1 seed) | Re-measured, pooled 95% CI | Verdict |
|---|---:|---:|---|
| A model at all, vs last-5 average | +19% | **+614** [+361, +876] · +15% | ✅ **better** |
| Hit must gain 8, not 6 | +299 | −1 [−92, +97] | no detectable effect |
| Refit on all data after validating | +127 | +43 [−75, +171] · ahead 8 of 10 seed-seasons | no detectable effect |
| Betting-odds features | −32 | +15 [−82, +107] | no detectable effect |
| Team strength from recent xG instead of FPL's ratings (new) | — | 2025-26 −153 [−276, −24]; 2026-27 replay 267 vs 292 | worse — last season's FPL ratings stay |
| Count bench players for less than 12% (new) | — | backtest +15 to +25, CIs span zero · simulator −36 [−85, +11] | no detectable effect — stays 12% |
| Average five seed-different models (new) | — | starting XIs agreed between seeds 75–78% → 86–88%, all four seasons; points +25 [−37, +92] · held back +23 [−34, +82] | ✅ **shipped** — steadier picks, no cost |
| Injured/suspended later weeks by return dates and curves (new, step 3) | — | +4.7 [−26, +33] paired · 11 of 222 decisions changed | no detectable effect — stays off |
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
| Split populations vs starters-only for both stages | +7 | starters-only **+56** [+11, +103] on the tuning seasons — then +18 and −17 on the held-back seasons | ⚠️ **unconfirmed**: split populations stay |
| Backtest from GW2, not GW8 | — | — | kept: a coverage fix, not a points claim |

> **The confirmation step, used once.** Training *both* stages on established
> starters only — the setting this project had rejected — beat production by
> +56 [+11, +103] on the tuning seasons, ahead in both. The pre-registered test
> required it to stay positive in **both** held-back seasons. It scored +18 in
> 2022-23 and −17 in 2023-24 (pooled +1 [−65, +67]), so it is **unconfirmed** and
> production is unchanged. Without the held-back seasons it would have shipped.

### Not re-measured — unproven either way

Each of these sits inside the ±146-point band that changing only the seed
produces. The reasoning may well be right; the number doesn't show it.

| Idea | One-seed result | Reasoning at the time |
|---|---:|---|
| Per-position regressors | −104 | Splits the feature set too thin |
| Captain on ceiling, not mean | −75 | Chasing upside drags high-variance players into the whole squad |
| Early-season shrinkage | −64 | Multi-season training already covers the thin-history weeks |
| Set-piece / penalty features | −62 | Takers are just good players; MAE identical to 3 decimals. (Measured with a join that read the snapshot taken *after* the match — since fixed; a leak can only have flattered it) |
| Recency weighting by season | −58 | Lost both seasons |
| Single flat regressor | −53 | Smears rotation risk into quality |
| Free-transfer margin | split | −10 / +106 by season |
| Differential tilt | ≈0 | Buys rank variance — the right trade only when behind |

### Harness fixes, and how each was checked

A measurement fix is accepted on correctness and on moving totals the way it
should. One that moves them the wrong way points at a bug in the fix — which is
exactly how the 2025-26 "available, 0% chance" artefact was caught.

| Fix | Expected | Measured |
|---|---|---|
| Predict a double-gameweek player per match | more points in double weeks | +94 and +43 — every point in the 7 double weeks; +137 [+34, +273] |
| Deadline prices in multi-week projections | the leak flattered simulator totals | higher with the leak in both seasons for both procedures (+101 and +65 pooled; 7 of 8 seed-seasons; inside the noise) |
| Pre-deadline injury flags | better accuracy | MAE 1.086 → 0.996 and 0.991 → 0.911; Brier P(60+) 0.097 → 0.089 and 0.084 → 0.079; points −9 [−53, +33] |
| Each season's own transfer rules | correct counts | unit tests; the first-week rule reproduces a real team's history |
| Simulator runs production's decision code | identical live output | identical recommendation before and after |
| Old-harness mode | reproduces the pre-audit numbers | exactly, all six seed × season totals (checked before ten duplicated 2025-26 archive rows were removed, which moves that season by a few points) |

> The whole corrected harness scores the same model **+128 points** higher than
> the old one ([+12, +274]) — almost all of it the double-gameweek fix.

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
# five seeds; per-gameweek results kept as JSON
python -m data_engine.backtest --augment \
       --variants production your_new_variant \
       --seeds 42 7 13 101 2024 --out bt.json

# faster while iterating — every 3rd gameweek, one seed (screening only)
python -m data_engine.backtest --seasons 2025-26 --stride 3
```

### Test a transfer-planner change

```bash
python -m data_engine.season_sim --augment \
       --policies production your_policy --seeds 42 7 13 --out sim.json
```

### Test a planner change with less noise

```bash
python -m data_engine.season_sim --augment --policies production \
       --branch production:your_policy --seeds 42 7 13 --out branch.json
```

The **paired branch test**: each week the candidate decides from production's
exact position, and both decisions are scored on realised points over the next
six weeks, holding the squad. Weeks where they agree count as exactly zero, so
it isn't drowned by the simulator's season-long drift (100–240 points between
seeds). Use `--block 6` when evaluating it — consecutive branches overlap.

### Turn results into a verdict

```bash
python -m data_engine.evaluation bt.json other.json --reference production
```

Prints each variant's mean and spread across seeds per season, then the paired
difference to production with its 95% interval and the verdict (better / worse
/ no detectable effect). Files from different machines or days pool freely.

> **Running seasons in parallel:** `--seasons 2025-26 --prior-seasons 2024-25`
> runs one season exactly as `--augment` would, so each season (or each seed)
> can be its own process. A backtest season takes ~6 minutes per seed. A
> simulator season takes 20 minutes to 2 hours — some weeks' solves hit the
> 120-second limit — so long simulator races belong on the **Season simulation**
> GitHub Action.

> **The old harness** is still available for one cycle: `--legacy-doubles` and
> `--no-availability` on the backtest, `--legacy-prices`, `--legacy-rules` and
> `--no-availability` on the simulator. With them, the backtest reproduces the
> pre-audit totals exactly.

---

## 10 · Every knob in config.py

Each carries an inline comment with its verdict and the exact numbers behind it.
**Changing any of them without re-running a harness undoes evidence.**

| Setting | Value | Meaning |
|---|---:|---|
| `HORIZON_GWS` | 6 | Gameweeks planned at once |
| `HORIZON_DECAY` | 0.85 | Discount per week into the future |
| `HIT_MARGIN` | 4.0 | A hit must gain 4+4=8. Re-measured: no setting beats it, none is distinguishable |
| `FREE_TRANSFER_MARGIN` | 0.0 | Free transfers cost nothing. Tested at 1.5 — a split |
| `DIFFERENTIAL_WEIGHT` | 0.0 | Tilt toward unowned players. Points-neutral; situational |
| `MAX_FREE_TRANSFERS` | 5 | Real cap (official rules + live API). Was wrongly 2 |
| `BENCH_WEIGHT` | 0.12 | Autosub insurance value |
| `CAPTAIN_QUANTILE` | 0.80 | Ceiling model's quantile. Built, rejected twice, kept off |
| `VALIDATION_HOLDOUT_GAMEWEEKS` | 5 | Time-based holdout size |
| `SOLVER_TIME_LIMIT` | 120s | Near-optimal before the deadline beats perfect after it |
| `ATTACH_ODDS` | False | Rejected −32 |
| `ATTACH_SETPIECE` | False | Rejected −62 |
| `MODEL_SEED` | 42 | XGBoost's seed. The harnesses override it per `--seeds` run |
| `MODEL_BAG_SIZE` | 5 | Models averaged, each with its own seed. Shipped Oct 2026: steadier picks, no cost |
| `TUNING_SEASONS` | 2024-25, 2025-26 | What variants are chosen on |
| `CONFIRMATION_SEASONS` | 2022-23, 2023-24 | Held back; run once per accepted change |
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
| `weekly.yml` | Every 4 hours (cron) | Checks the next deadline and exits in seconds unless one is within ~30h. Otherwise refreshes, retrains, re-solves, commits — which triggers a Vercel redeploy |
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
- **Close start/bench calls are close to coin flips.** When two players'
  projections differ by under a point, the higher one outscores the other only
  52–57% of the time in a given week (2024-26, ties left out), and 75% even at a
  3-point gap. The edge shows over a season, not in every week. Tested for
  bias by player type in October 2026 (research/2026-10-projection-bias): none.
- **It can't see team news beyond FPL's own flags.** From 2024-25 the harnesses
  see the injury flags FPL published before each deadline; they still can't see
  a press conference that hasn't reached the flags.
- **The simulator is noisy.** The same policy can finish 100–240 points apart
  on different model seeds, because one different early transfer sends the
  whole season down another path. With three seeds it can't resolve effects
  much under ~100 points, which is why most planner verdicts read "no
  detectable effect".
- **Neither harness plays chips.** Both totals sit below a real chip-using season.
  They're comparative yardsticks, not season predictions.
- **Predictions are conditional means on a violently skewed distribution.** Among
  players who start, real scores spread 3.16 points; predictions spread 1.28.
  That compression is mathematically correct and is why expected points alone
  will never identify who's about to haul.

### Genuinely open

- **Hard injury flags last six weeks in the planner — and it barely matters.**
  A suspended or injured player is valued at a tenth of his projection for every
  week of the horizon, although suspended regulars play ~82% as often as fit
  ones the very next week. `horizon_availability.py` fixes the valuation with
  FPL's return dates and measured return curves. Tested with the paired branch
  test it changed **11 of 222** weekly decisions: +4.7 [−26, +33], no detectable
  effect. An injured player you own scores nothing next week either way, so the
  planner benches or sells him either way. It's in the code, switched off.

- **Newly appointed set-piece takers.** The duty itself adds nothing — but a
  player who just *inherited* penalties has a history that can't show it yet.
  That needs a change-detection feature (duty this week he didn't have last
  week), not the duty. Data and join are already in place.
- **The odds re-test reproduced the old numbers exactly** despite the data
  demonstrably differing — and on five seeds the variant is no detectable
  effect (+15 [−82, +107]), so "rejected" was always stronger than the
  evidence. The coincidence isn't explained.
- **A decoupled captain test** — pick the squad on the mean, then the captain on
  ceiling — was never run. It would separate the two effects the rejected test
  conflated.

### 🔑 If you change one thing, change this

Keep the rule. Every knob in `config.py` carries its verdict because the
alternative is folklore — a codebase full of settings nobody remembers the reason
for. When you test something new, write the number down next to the setting,
whichever way it goes.

---

*Compiled September 2026, harness and ledger revised after the October 2026
audit. Evidence: multi-seed walk-forward backtests over 2024-25 and 2025-26,
transfer-constrained season simulation, live FPL API. Not affiliated
with the Premier League or Fantasy Premier League.*
