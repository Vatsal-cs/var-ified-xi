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

# Transfer economy. One free transfer is earned per gameweek; unused ones
# bank up to a maximum of 2 available at once (this week's plus one rolled
# over) — NOT 5. Verified against a real entry's history (GW2 0 used -> GW3
# had 2 available; GW3 1 used, GW4 0 used -> GW5 had 2 available, not 3 as
# the old cap of 5 would predict). Anything beyond what's banked costs points.
MAX_FREE_TRANSFERS = 2
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

# Used when a player's birth date isn't available (some new signings, and
# ALL historical-season rows, since that dataset doesn't include birth
# dates). A neutral fallback avoids biasing the model toward "age == 0",
# which would read as an implausible outlier rather than "unknown".
FALLBACK_AGE = 26.0

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
BENCH_WEIGHT = 0.12   # bench players contribute a small fraction to objective
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
ATTACH_ODDS = False