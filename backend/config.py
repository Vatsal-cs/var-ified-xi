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

# ---------------------------------------------------------------------------
# ML feature engineering
# ---------------------------------------------------------------------------
ROLLING_WINDOWS = [3, 5]        # gameweeks, for rolling form features
MIN_MINUTES_HISTORY = 1         # drop rows where player didn't play at all
TARGET_COL = "total_points"

FEATURE_COLUMNS = [
    "minutes_avg_3",
    "minutes_avg_5",
    "points_avg_3",
    "points_avg_5",
    "ict_index_avg_3",
    "influence_avg_3",
    "creativity_avg_3",
    "threat_avg_3",
    "form",
    "was_home",
    "team_strength_attack",
    "team_strength_defence",
    "opp_strength_attack",
    "opp_strength_defence",
    "fixture_difficulty",
    "now_cost",
    "selected_by_percent",
    "element_type",
    "days_since_last_match",
    "age",
    "xgi_avg_3",
    "xgc_avg_3",
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
# Optimizer weights
# ---------------------------------------------------------------------------
BENCH_WEIGHT = 0.12   # bench players contribute a small fraction to objective
CAPTAIN_MULTIPLIER = 1.0  # extra points added on top of base (captain scores 2x total)