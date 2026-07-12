"""
File: config.py
Path: fpl-optimizer/backend/config.py

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
]

# ---------------------------------------------------------------------------
# Optimizer weights
# ---------------------------------------------------------------------------
BENCH_WEIGHT = 0.12   # bench players contribute a small fraction to objective
CAPTAIN_MULTIPLIER = 1.0  # extra points added on top of base (captain scores 2x total)
