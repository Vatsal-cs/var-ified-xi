"""
File: config.py
Path: var-ified-xi/backend/config.py

Central configuration: API endpoints, squad rules, MILP weights, and file paths.
Nothing in this file makes network calls — pure constants.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parent
DATA_DIR = BACKEND_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = DATA_DIR / "output"
MODELS_DIR = BACKEND_ROOT / "models"

# Where the frontend expects its static data file.
# Adjust if your frontend folder name/location differs.
FRONTEND_PUBLIC_DIR = BACKEND_ROOT.parent / "frontend" / "public"

for d in (RAW_DIR, OUTPUT_DIR, MODELS_DIR, FRONTEND_PUBLIC_DIR):
    d.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODELS_DIR / "xgb_points_model.pkl"
OUTPUT_JSON_PATH = OUTPUT_DIR / "optimized_team.json"
FRONTEND_JSON_PATH = FRONTEND_PUBLIC_DIR / "optimized_team.json"

# Injury/availability log — persists ACROSS runs (unlike RAW_DIR, which is
# a same-day cache). This file is intentionally NOT in .gitignore's
# data/raw or data/output patterns, so it should be committed to git —
# it's the accumulated history that makes "times flagged this season"
# meaningful instead of resetting to zero on every fresh clone.
INJURY_LOG_PATH = DATA_DIR / "injury_log.json"

# Your own captain/vice for a gameweek, overriding the model's (main.py).
OVERRIDES_PATH = BACKEND_ROOT / "overrides.json"

# ---------------------------------------------------------------------------
# Team-news reader (data_engine/team_news.py)
# ---------------------------------------------------------------------------
# An AI model with web search reads the latest team news for the clubs that
# matter to you: Gemini 2.5 Flash with Google Search (free; GEMINI_API_KEY), or
# Claude (paid; ANTHROPIC_API_KEY) — GitHub Actions secrets in the cloud. Off
# without either. "Out" and "doubtful" calls lower the projection like an FPL flag
# would (TEAM_NEWS_ADJUST), only when worse than FPL's own flag and sourced
# from the last few days; "rotation risk" is shown, never applied. Untestable
# on past seasons (no archived press conferences), so every call is logged to
# TEAM_NEWS_LOG_PATH and judged live against who actually played.
TEAM_NEWS_ENABLED = True
TEAM_NEWS_ADJUST = True
# Free-tier Gemini text models, tried in order. They read headlines we fetch
# (Google News, BBC Sport) — on the free tier only the 2.5 models can search,
# and those are closed to new projects. The key's project has no billing, so
# nothing here can cost money.
# Flash-Lite first: it barely "thinks" by default, so it answers in seconds;
# 3.8 Flash (asked to think little) is the fallback.
TEAM_NEWS_GEMINI_MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
TEAM_NEWS_MODEL = "claude-sonnet-5-5"         # used instead only if ANTHROPIC_API_KEY is set and Gemini's isn't
TEAM_NEWS_MAX_SEARCHES = 5          # per call; a call covers up to 4 clubs
TEAM_NEWS_WINDOW_HOURS = 48         # only read the news this close to a deadline
TEAM_NEWS_TTL_HOURS = 3             # reuse a result this fresh instead of paying again
TEAM_NEWS_PATH = DATA_DIR / "team_news.json"
TEAM_NEWS_LOG_PATH = DATA_DIR / "team_news_log.json"
# The last call per player per gameweek, kept for the whole season (the log
# above keeps only recent reads): what team_news.judge() scores.
TEAM_NEWS_CALLS_PATH = DATA_DIR / "team_news_calls.json"

# ---------------------------------------------------------------------------
# FPL public API (no auth required)
# ---------------------------------------------------------------------------
FPL_BASE_URL = "https://fantasy.premierleague.com/api"
BOOTSTRAP_URL = f"{FPL_BASE_URL}/bootstrap-static/"
FIXTURES_URL = f"{FPL_BASE_URL}/fixtures/"
ELEMENT_SUMMARY_URL = f"{FPL_BASE_URL}/element-summary/{{player_id}}/"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (FPL-Optimizer-Local-Engine/1.0)"
}
REQUEST_TIMEOUT = 15  # seconds
REQUEST_DELAY = 0.15  # polite delay between per-player API calls (seconds)

# ---------------------------------------------------------------------------
# Squad rules (standard FPL classic rules, 2024/25+)
# ---------------------------------------------------------------------------
SQUAD_SIZE = 15
BUDGET = 1000  # FPL prices are in tenths of a million; 1000 = £100.0m

# element_type in bootstrap-static: 1=GK, 2=DEF, 3=MID, 4=FWD
POSITIONS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

SQUAD_POSITION_LIMITS = {  # exact counts required in the 15-man squad
    1: 2,  # GK
    2: 5,  # DEF
    3: 5,  # MID
    4: 3,  # FWD
}

# Valid starting-XI position ranges (must sum to 11, GK fixed at 1)
STARTING_XI_LIMITS = {
    1: (1, 1),   # GK
    2: (3, 5),   # DEF
    3: (2, 5),   # MID
    4: (1, 3),   # FWD
}

MAX_PLAYERS_PER_CLUB = 3

# Transfer economy. One free transfer is earned per gameweek and unused ones
# bank up to FIVE at once (rule since 2024/25, confirmed for 2026/27 by the
# Premier League and by the live API: game_settings.max_extra_free_transfers
# is 4, i.e. one plus four banked). entry_data warns if the API ever disagrees.
#
# This was 2 for a while. The evidence for 2 was a real entry holding two
# free transfers at GW5 — but that entry was created at GW2, and a team's
# first gameweek is a free squad pick that banks nothing. With that accrual
# rule, a cap of 5 reproduces the observed counts too (GW5 = 2, GW6 = 1), so
# the observation never distinguished the caps; the official rules do.
MAX_FREE_TRANSFERS = 5
TRANSFER_HIT_COST = 4  # points deducted per extra transfer

# ---------------------------------------------------------------------------
# ML feature engineering
# ---------------------------------------------------------------------------
ROLLING_WINDOWS = [3, 5]        # gameweeks, for rolling form features
MIN_MINUTES_HISTORY = 1         # drop rows where player didn't play at all

# Early-season shrinkage: blend rolling averages toward the positional norm
# in proportion to how few matches back them (n/(n+k) weight on the
# observation). Sounded obviously right; the backtest disagreed — with the
# harness extended to start at gameweek 2, the plain pipeline scored 4587
# simulated points across 2024-25 + 2025-26, against 4545 with a
# matches_played feature and 4481 with that feature plus k=3 shrinkage.
# Multi-season historical training already carries the model through the
# thin-history weeks, and a forced discount only blunts real early signal.
# OFF by default; to re-test, set this knob and re-run backtest.py (it acts
# at feature-build time, so it can't be an in-harness variant).
FORM_SHRINKAGE_GAMES = 0.0
TARGET_COL = "total_points"

# The model's input columns. Every one of these is produced identically for
# live FPL data and for the historical archive (see
# feature_engineering.ROLLING_FEATURE_SPEC), so the training and prediction
# distributions match. Anything only available live — injury-flag history,
# set-piece order — is deliberately NOT here; it is applied as a
# prediction-time adjustment instead. See REPEAT_FLAG_THRESHOLD below.
FEATURE_COLUMNS = [
    # Form
    "minutes_avg_3",
    "minutes_avg_5",
    "points_avg_3",
    "points_avg_5",
    "ict_index_avg_3",
    "influence_avg_3",
    "creativity_avg_3",
    "threat_avg_3",
    "form",
    # Underlying chance quality
    "xgi_avg_3",
    "xgc_avg_3",
    "xg_avg_3",
    "xg_avg_5",
    "xa_avg_3",
    "xa_avg_5",
    # Bonus-point potential
    "bps_avg_3",
    "bps_avg_5",
    "bonus_avg_5",
    # Rotation / starting risk
    "starts_avg_3",
    "starts_avg_5",
    # Defensive scoring (defensive contribution, clean sheets, saves)
    "dc_avg_3",
    "dc_avg_5",
    "saves_avg_3",
    "cs_avg_5",
    "gc_avg_3",
    # Fixture context
    "was_home",
    "team_strength_attack",
    "team_strength_defence",
    "opp_strength_attack",
    "opp_strength_defence",
    "fixture_difficulty",
    # Player context
    "now_cost",
    "selected_by_percent",
    "element_type",
    "days_since_last_match",
    "age",
    # NOT here, though it sounds like it should be: "matches_played" (how many
    # games back the form averages). Tested alongside the early-season
    # shrinkage idea after the GW1-form-chasing scare; with the backtest
    # extended to start at gameweek 2, the plain pipeline scored 4587
    # simulated points across 2024-25 + 2025-26, matches_played 4545, and
    # matches_played + shrinkage 4481. Multi-season training already covers
    # the thin-history regime. The column is still computed by
    # feature_engineering for future experiments — it is just not a model
    # input.
]

# Team quality from each team's own recent expected goals (team_form.py),
# replacing FPL's published strength ratings — set before the season, and not
# published at all for 2026-27.
#
# TESTED (Oct 2026, research/2026-10-team-form): backtest +34 in 2024-25 but
# -153 [-276, -24] in 2025-26; on the 2026-27 GW2-5 replay it scored 267 vs
# 292 for last season's FPL ratings, worse on every seed. A handful of
# matches of xG is noisier than a whole season's rating. Stays off; the live
# fallback (last season's ratings) stays.
TEAM_FORM = False

# What team form is built from: "xg" (each match's expected goals) or "odds"
# (the goals betting odds expected before each match, odds_data.py). Research
# only. TESTED (Oct 2026, research/2026-10-market-ratings): odds-based team
# form added to last season's ratings, +1 [-107, +111] — no detectable effect.
TEAM_FORM_SOURCE = "xg"

# Research only: when replaying a past season, rate its teams with the
# PREVIOUS season's published ratings — exactly what the live model has to do
# in 2026-27 — instead of that season's own (which the archive may have saved
# with hindsight). Never affects live runs.
LAGGED_TEAM_RATINGS = False
# Research only: lag the ratings for these seasons alone. The backtest's
# live_ratings variant sets it to the replayed season, so the model trains on
# earlier seasons' own ratings and plays the replayed one on last season's —
# exactly how the live model runs in 2026-27 (research/2026-10-stale-ratings).
LAGGED_TEAM_RATINGS_SEASONS = ()

# Ownership (selected_by_percent) as a model input. It has been in
# FEATURE_COLUMNS all along but was 0 in every training row — the archive's
# ownership is kept under another name and this season's rows never carried
# it — so the trees never used it, while live rows held real percentages.
# With this on, training rows get the share of managers owning the player
# that gameweek (archive: selections / (total / 15); this season: the same
# from FPL's per-gameweek `selected`), in percent like the live value.
# Under test: research/2026-10-ownership.
OWNERSHIP_FEATURE = False
TEAM_FORM_COLUMNS = ["team_xg_for", "team_xg_against", "opp_xg_for",
                     "opp_xg_against", "match_xg_for", "match_xg_against"]
TEAM_FORM_REPLACES = ["team_strength_attack", "team_strength_defence",
                      "opp_strength_attack", "opp_strength_defence", "fixture_difficulty"]


def team_form_features(base: list) -> list:
    """The feature list with FPL's strength ratings swapped for team form."""
    return [c for c in base if c not in TEAM_FORM_REPLACES] + list(TEAM_FORM_COLUMNS)


if TEAM_FORM:
    FEATURE_COLUMNS = team_form_features(FEATURE_COLUMNS)

# Used when a player's birth date isn't available (some new signings, and
# ALL historical-season rows, since that dataset doesn't include birth
# dates). A neutral fallback avoids biasing the model toward "age == 0",
# which would read as an implausible outlier rather than "unknown".
FALLBACK_AGE = 26.0

# Real ages are OFF: every player gets FALLBACK_AGE. Found Oct 2026 (GW7):
# the historical rows all carry 26.0, so only this season's rows had a real
# age, and the trees used it as a name tag — an age nobody else has picked
# out one player's own matches. Henderson (36, two starts, one 18-pointer)
# got +4.3 on his points-if-60+ from age alone (2.4 -> 5.1 projected), Groß
# +1.3. Every backtest replays archive seasons where age is always 26, so
# the tested model never used age; this makes live runs match it. Turn on
# only with birth dates for the historical seasons too, and a backtest.
PLAYER_AGE = False

# Rows/predictions with fewer rest days than this are flagged as short-rest
# in the output (informational — the model already sees days_since_last_match
# as a raw feature, this is just for the "why" surfaced to the frontend).
SHORT_REST_THRESHOLD_DAYS = 4

# ---------------------------------------------------------------------------
# Multi-season historical training data
# ---------------------------------------------------------------------------
# Past COMPLETED seasons pulled from the open-source vaastav/Fantasy-Premier-
# League archive to give the model far more (features -> points) examples
# than the current season alone can provide — especially valuable early in
# a season, or during the close season when the current season has no data
# yet. Never used for prediction, only concatenated into TRAINING data (see
# historical_data.py). Add/remove seasons here as more become available.
HISTORICAL_SEASONS = ["2023-24", "2024-25", "2025-26"]
HISTORICAL_DATA_BASE_URL = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"

# Which completed seasons the research harnesses may tune on, and which are
# held back. A change is chosen on TUNING_SEASONS; it is accepted only if its
# effect keeps the same sign when run ONCE on CONFIRMATION_SEASONS, which are
# never used to pick between variants. Looking at them while choosing turns
# them into tuning seasons, and then nothing is left to confirm against.
# Availability history (FPL-Core-Insights) starts in 2024-25, so experiments
# that depend on it have no back-season confirmation: their holdout is the
# live 2026-27 season.
#
# Uses so far: Oct 2026, backtest variant legacy_filtered (+56 on tuning,
# then +18 / -17 here) — unconfirmed, not shipped.
#                Oct 2026, seed averaging (bagged5): points not worse
#                (+23), steadier picks in both — confirmed, shipped.
#                Oct 2026, other_matches (cup/European/international load):
#                +87 [+13, +159] on tuning, then +43 / +11 here — confirmed,
#                shipped.
TUNING_SEASONS = ["2024-25", "2025-26"]
CONFIRMATION_SEASONS = ["2022-23", "2023-24"]

# XGBoost's random seed. Changing ONLY this moves a two-season backtest by up
# to ~175 points with accuracy unchanged, so the research harnesses run
# several seeds (--seeds) and report the spread; production keeps 42.
MODEL_SEED = 42

# Matches FPL doesn't show — Champions/Europa/Conference League, League Cup,
# FA Cup, and internationals — as model inputs (data_engine/other_matches.py):
# rest since the club's last other match, the next one coming, whether the
# player started it, and his international load.
#
# SHIPPED (Oct 2026, research/2026-10-other-matches): +87 [+13, +159] on the
# tuning seasons (+67, +20; 9 of 10 runs ahead), then +43 and +11 on the
# held-back 2022-23 and 2023-24 — positive in both, as pre-registered. Form in
# those games (goals, shots) was tested alongside: +81 [-4, +168], not better,
# so only the rest-and-load inputs are used.
OTHER_MATCHES = True
OTHER_MATCH_COLUMNS = ["xm_days_before", "xm_days_after", "xm_count_14", "xm_started_before",
                       "xm_rested_before", "intl_apps_14", "intl_starts_14", "intl_far_14",
                       "intl_days_before"]

# Pull the points-if-60+ projection toward its position's average:
# mean + k * (projection - mean). None = off. {"k": 0.65} for one factor,
# {"k_by_pos": {1: .., 2: .., 3: .., 4: ..}} per position.
#
# TESTED (Oct 2026, research/2026-10-projection-shrink): -1 [-54, +53] on the
# tuning seasons (+20, -21), per position -21. Accuracy a little better, picks
# barely change, points don't move. Stays off.
CONDITIONAL_SHRINK = None

# Seed averaging: train this many copies of the model, each with a different
# seed (MODEL_SEED, then MODEL_SEED + 7919, ...), and average their
# projections. 1 is a single model.
#
# SHIPPED at 5 (Oct 2026, research/2026-10-seed-averaging). Pre-registered
# as "steadier picks at no cost": across 5 run seeds the starting XI two
# independently-trained versions share rose from 75-78% to 86-88% in all
# four seasons, captain agreement from 70-81% to 81-89%, accuracy improved
# slightly everywhere, and points were not worse — +25 [-37, +92] on the
# tuning seasons, +23 [-34, +82] on the held-back ones. Costs four extra
# model fits per run.
MODEL_BAG_SIZE = 5

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
# Time-based holdout: hold out the most recent N gameweeks as validation
# instead of a random split. FPL data is a time series — random splits let
# the model "peek" at future gameweeks during training, which inflates the
# reported accuracy. This gives an honest, if slightly worse-looking, MAE.
VALIDATION_HOLDOUT_GAMEWEEKS = 5

# A position needs at least this many 60+-minute training rows before it gets
# its own stage-2 regressor; below it, the pooled regressor is used instead.
# Guards against a badly overfit model for a thin position early in a season.
MIN_ROWS_PER_POSITION = 400

# ---------------------------------------------------------------------------
# Injury/availability dampening
# ---------------------------------------------------------------------------
# A player flagged as fitness-doubtful this many times or more (even if
# currently marked "available") gets an extra caution multiplier applied
# at PREDICTION time only — never used as a trained model feature, since
# we don't have this history retroactively for past gameweeks and adding
# it as a feature would create a train/predict distribution mismatch.
REPEAT_FLAG_THRESHOLD = 3
REPEAT_FLAG_DAMPEN_FACTOR = 0.85

# Availability in the weeks AFTER next for injured and suspended players
# (data_engine/horizon_availability.py): FPL's return dates where the news
# gives one, measured return curves where it doesn't. Off means a hard flag
# keeps a player at a tenth of his projection for the whole horizon — which
# writes off a one-match suspension for six weeks.
#
# TESTED (Oct 2026, research/2026-10-horizon-availability): no detectable
# effect. Paired branch test +4.7 [-26, +33] (2024-25 +5, 2025-26 0); full
# season -8 [-69, +41]. It changes 49-61 players' projections a week but only
# 11 of 222 weekly decisions, each worth -13 to +25: an injured player you own
# scores nothing next week under either rule, so he's benched or sold either
# way. Failed its pre-registered bar, so it stays off. The rule is sound and
# harmless; it just almost never decides anything.
HORIZON_AVAILABILITY = False

# ---------------------------------------------------------------------------
# Planning horizon
# ---------------------------------------------------------------------------
# How many gameweeks ahead to predict and optimize over. Planning only one
# gameweek ahead is how you end up buying a player for one great fixture and
# then watching him face the top three defences in a row. Six weeks is the
# usual sweet spot: far enough to see a fixture swing, near enough that form
# and team news still mean something.
HORIZON_GWS = 6

# Future gameweeks are discounted in the objective — a point next week is
# worth more than a projected point five weeks out, because the projection is
# less certain and because you can always transfer again before then.
HORIZON_DECAY = 0.85

# ---------------------------------------------------------------------------
# Optimizer weights
# ---------------------------------------------------------------------------
# Share of a bench player's projection the optimizers count. TESTED (Oct
# 2026, research/2026-10-bench-weight): 0.06 / 0.03 / 0.01 were each no
# detectable effect in the backtest (+15 to +25, CIs spanning zero), and 0.03
# did slightly worse in the transfer-constrained simulator (-36 [-85, +11]).
# Stays 0.12. The live team's expensive bench came from the squad builder's
# HORIZON_SQUAD_WEIGHT at team creation, not from this.
BENCH_WEIGHT = 0.12
CAPTAIN_MULTIPLIER = 1.0  # extra points added on top of base (captain scores 2x total)

# How heavily squad membership is rewarded for its whole-horizon value on top
# of this gameweek's points. horizon_points is a decayed sum over HORIZON_GWS
# (roughly 4x a single gameweek), so 0.3 makes future fixtures matter about
# as much as the coming one without letting them dominate it.
HORIZON_SQUAD_WEIGHT = 0.3

# ---------------------------------------------------------------------------
# Transfer planner (multi-gameweek MILP)
# ---------------------------------------------------------------------------
# The full player pool across a six-gameweek horizon is a far bigger integer
# program than CBC wants to prove optimal. Restricting each position to its
# best candidates costs nothing real — a midfielder outside the top 60 by
# projected points over the horizon was never going to be transferred in —
# and turns a multi-hour solve into a few seconds. Players already in your
# squad are always included regardless of where they rank.
CANDIDATE_POOL_PER_POSITION = {
    1: 20,   # GK
    2: 55,   # DEF
    3: 60,   # MID
    4: 35,   # FWD
}

# Seconds before the solver returns its best plan so far instead of continuing
# to prove optimality. A near-optimal plan delivered before the deadline beats
# a perfect one delivered after it.
SOLVER_TIME_LIMIT = 120

# A points hit (-4) is only worth taking if the transfer gains clearly MORE
# than 4 — breaking even on paper isn't worth the certainty of losing 4,
# since the projection might be wrong. The planner treats a hit as costing
# TRANSFER_HIT_COST + HIT_MARGIN when deciding whether to take one, so a hit
# only shows up when the decay-weighted gain over the horizon clears ~8.
#
# Verdict (season_sim.py, transfer-constrained, GW2-38, both seasons):
#
#     margin  2025-26   2024-25   pooled      hits taken
#     2.0        base      base     base      57   (-228 pts)
#     4.0        +154      +145     +299      32   (-128 pts)   <- shipped
#     6.0         +48        -6      +42      13    (-52 pts)   split
#
# At 2.0 the planner spent 228 points on hits across two seasons and finished
# BEHIND a policy that took none at all: it was buying hits that didn't pay
# for themselves. At 6.0 it becomes too timid and loses 2024-25. 4.0 wins both
# seasons by a similar margin, which is the bar, and is worth about four
# points a gameweek — the largest single improvement measured in this project.
#
# RE-MEASURED (Oct 2026) — that table measured a different game: a bank of 2
# in seasons that allowed 5, a solver that planned and took hits in any week
# (production only advises one, this week), and future prices leaking into
# the horizon. With those fixed, running the shipping procedure (planner.py),
# 3 seeds per season, against 4.0:
#
#     margin  2024-25   2025-26   pooled [95% CI]        verdict
#     0.0       -82       +13      -69 [-186, +48]       no detectable effect
#     2.0       -43       +44       +1  [-97, +92]       no detectable effect
#     6.0       +54        -7      +47  [-64, +155]      no detectable effect
#     no hits   +62       -19      +44  [-95, +196]      no detectable effect
#
# Nothing beats 4.0 and nothing is distinguishable from it; the direction
# flips between seasons. It stays because nothing won, not because it's proven.
HIT_MARGIN = 4.0

# The same idea for transfers that cost no points. A free transfer looks free,
# so with no margin the solver makes one every single week: there is always
# SOME player projecting 0.1 higher, and nothing in the objective to say that
# 0.1 is indistinguishable from zero. Three real costs are invisible to it —
# the option value of banking toward two transfers, the ability to react to
# team news you don't have yet, and the fact that the projected gain carries
# an error bar of about 1.3 points per player per week.
#
# So a free transfer is charged this many expected points. season_sim.py is
# the harness that decides the value — the first thing in this project able to
# measure a transfer-planner setting at all.
#
# Verdict: 0.0. A margin of 1.5 looked like a clear +96 when both seasons were
# pooled, and turned out to be a SPLIT once they were reported separately
# (-10 in 2025-26, +106 in 2024-25) — exactly the case the every-season rule
# exists to catch. And once HIT_MARGIN was corrected to 4.0 the knob stopped
# binding at all: free transfers at 0.0 and at 1.5 produce identical seasons,
# because a planner that isn't buying bad hits wasn't making marginal free
# transfers either. The churn this was written to fix was a symptom of
# underpriced hits, not of underpriced free transfers.
#
# Kept, with the objective term wired up, because it costs nothing and the
# finding is worth being able to re-run. Raise it only with new evidence.
FREE_TRANSFER_MARGIN = 0.0

# The quantile of points-given-a-start that the ceiling regressor is fit to.
# 0.80 = "a good day, not a miracle". The theory: the armband doubles one
# player, so what you want is the biggest realistic haul, not the safest
# average.
#
# TESTED TWICE, REJECTED TWICE. The column is still produced, and both
# harnesses can still race it, but nothing uses it by default.
#
#   1. backtest.py (squad rebuilt from scratch each week): 4609 vs 4617
#      across two seasons. Within noise, so not really a verdict either way.
#
#   2. season_sim.py (transfer-constrained, the real test — and the first one
#      that actually EXERCISED it, since plan_transfers previously ignored
#      the captain column entirely):
#
#         2025-26   -10      captain pts 231 vs 222
#         2024-25   -65      captain pts 302 vs 312
#         pooled    -75
#
#      Lost both seasons, which is the bar. The 2025-26 line is the
#      interesting one: captaining on upside DID earn more captain points
#      there and still lost overall, because valuing the armband on ceiling
#      also pulls high-variance players into the squad and the squad lost
#      more than the armband gained.
#
# The one test not yet run is the decoupled version: choose the squad on the
# mean, then pick the captain from the finished XI on the ceiling. That would
# separate the two effects the run above conflates. 2024-25 argues against it
# (captain points fell there too), so it is not obviously worth the work.
CAPTAIN_QUANTILE = 0.80

# Older training seasons are down-weighted by this factor per season of
# age (current season = 1.0, newest past season = 0.7, the one before
# 0.49, ...). Every gameweek WITHIN a season keeps equal weight — this is
# season-level recency only, not within-season, on purpose. 1.0 disables
# it. backtest.py's `recency` variant is the A/B.
# Verdict (backtest, GW2-38, 2024-25 + 2025-26, --augment): season-level
# recency weighting scored 4559 vs 4617 for equal weighting — it lost
# both seasons. Kept as backtest.py's `recency` variant. 1.0 = disabled.
RECENCY_SEASON_DECAY = 1.0

# Set-piece duty features (setpiece_data.py): who takes the penalties, free
# kicks and corners, encoded as 1/order with 0 for everyone else. Penalty
# takers in this season's data average 5.28 pts/90 against 4.32 for
# non-takers, and the model has never been shown any of it.
#
# Left out originally because the vaastav training archive has no set-piece
# columns, which would have meant a feature that exists at prediction time
# and not at training time. olbauday/FPL-Core-Insights publishes the same
# fields per gameweek for 2024-25 and 2025-26, which removes that objection.
# 2023-24 is not covered and gets zeros.
#
# Verdict (backtest.py, GW2-38, both seasons, --augment): REJECTED.
#
#     variant     2024-25   2025-26   pooled      MAE          rank-r
#     production     2337      2280     4617   1.087/0.992   .653/.716
#     setpiece       2309      2246     4555   1.084/0.991   .654/.716
#
# Lost both seasons. The important column is MAE, not points: it is identical
# to three decimals, and so is rank correlation. The model is not using these
# features at all, so the -62 is tree-structure noise rather than active harm.
#
# Why the raw +22% didn't survive: it was confounded by quality. Penalty
# takers are good players, and the model already knows they are good — their
# penalty income is sitting in their own xG, threat, bps and points averages,
# which are already features. "He is the designated taker" adds almost no
# information once you have seen what he actually scores.
#
# The case this does NOT test is the one worth wanting: a player who has just
# INHERITED the job, whose history cannot show it yet. That is a handful of
# players a season, and isolating it needs a change-detection feature (duty
# this week that he did not have last week) rather than the duty itself.
# Worth trying if someone wants to; the data and the join are already here.
#
# Kept wired up and off, per the convention for rejected ideas in this file.
ATTACH_SETPIECE = False

# Tilt the transfer objective toward players the field doesn't own, by
# multiplying expected points by (1 + w * (1 - ownership)).
#
# The theory is sound and is NOT about expected points: your edge over a rival
# is your score minus theirs, so points you both scored cancel. A haul from a
# 70%-owned player keeps you level; the same haul from a 5%-owned player gains
# places. It buys rank variance, which is what you want when behind.
#
# Verdict (season_sim.py, both seasons): REJECTED at every weight tried.
#
#     weight   NET points   differential points
#     0.0            4183                  2951
#     0.2            4003 (-180)           2933 (-18)
#     0.5            3902 (-281)           3053 (+102)
#
# w=0.2 is strictly dominated: it loses 180 real points AND ends up with
# FEWER differential points than not tilting at all. w=0.5 does buy
# differential points, at an exchange rate of about 2.75 real points for each
# one — far too expensive to be worth taking.
#
# Those numbers were CONFOUNDED, and the confound turned out to be most of
# the effect. The tilt scales every value in the objective while the hit
# margin is a fixed quantity in those same units, so tilting quietly makes
# hits look cheaper: w=0.5 took 77 hits (-308 points) against baseline's 32
# (-128). Re-run with hits banned on both sides, which prices them equally:
#
#     policy              2025-26   2024-25   pooled   differential pts
#     no_hits                1927      2023     3950               2746
#     w=0.5, no hits         1858      2150     4008 (+58)         2917 (+171)
#
# So cleanly measured the tilt is roughly points-NEUTRAL — a split, losing
# 2025-26 by 69 and winning 2024-25 by 127 — while reliably buying 171
# differential points. Not the -281 disaster the first run showed; that was
# mostly the mispriced hits.
#
# Still 0.0 by default, because a split is a rejection by this project's
# standard and because points-neutral is not a reason to add complexity.
#
# But this is the one rejected idea here worth reconsidering BY SITUATION
# rather than for good. Roughly zero expected cost in exchange for rank
# variance is exactly the trade you want when you are behind and need to
# catch someone, and exactly the trade you do not want when you are ahead and
# protecting a lead. If it is ever turned on, it should also scale the hit
# margin by the same factor, or it will go hit-happy again.
DIFFERENTIAL_WEIGHT = 0.0

# Which mini-league the rival view analyses (rivals.py). None auto-picks the
# smallest classic league you're in, which is almost always the one you were
# actually invited to rather than the huge auto-joined ones (overall, your
# country, your club). Set an id to pin it.
RIVAL_LEAGUE_ID = None

# Betting-odds fixture features (odds_data.py) were joined onto training
# rows and tested: 4585 vs 4617, a split (helped 2025-26 +20, hurt
# 2024-25 -52). Rejected — the model's existing rolling xG/xGC and
# team-strength features already carry most of that signal, so the odds
# columns mostly added noise. The join is off unless this is set True
# (backtest.py's `odds` variant sets it); odds_data.py is otherwise unused.
#
# RE-TESTED 2026-09-23, after Variant.context was added so the join is live
# while rows are built. Suspicion at the time was that the original verdict
# had raced neutral constants. It reproduced EXACTLY — 4585 pooled, +20 and
# -52 by season — so the original verdict was sound and that suspicion was
# wrong. Recorded because a re-test that changes nothing is still evidence.
#
# Worth knowing for anyone tempted to try again: the model does use these
# columns when they are present (about 11% of stage-2 gain between them,
# odds_team_xg alone ranking alongside threat_avg_3). They are not ignored —
# they are used, and the squad still scores slightly worse. That is the
# stronger form of the rejection: bookmaker odds genuinely are informative
# about matches, and this model already extracts that information from
# rolling xG, xGC and team strength.
#
# RE-MEASURED (Oct 2026), 5 seeds per season on the corrected harness: +15
# pooled, 95% CI [-82, +107] (-15 in 2024-25, +31 in 2025-26). No detectable
# effect — so "rejected" was always stronger than one seed could support. It
# stays off: it adds a data dependency and shows no gain.
ATTACH_ODDS = False


# The shipped other-matches inputs join the model's inputs (defined above,
# after FEATURE_COLUMNS, so this has to come last).
if OTHER_MATCHES:
    FEATURE_COLUMNS = FEATURE_COLUMNS + [c for c in OTHER_MATCH_COLUMNS if c not in FEATURE_COLUMNS]
