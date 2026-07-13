"""
File: historical_data.py
Path: var-ified-xi/backend/data_engine/historical_data.py

Pulls multiple PAST completed Premier League seasons from the open-source
vaastav/Fantasy-Premier-League GitHub archive and reshapes them into the
exact same raw per-gameweek schema build_gameweek_history_df() produces —
so they flow through the SAME add_rolling_features() and
build_training_set() pipeline as live data, with zero duplicated logic.

This exists purely to give the model more (features -> points) examples to
learn from than the current season alone can provide — especially valuable
early in a season, or during the close season when the current season has
no data at all yet.

Bonus: this dataset already includes real per-gameweek expected goals (xG)
and expected assists (xA) data — the same fields FPL's own live API now
exposes — which get folded in as xgi_avg_3 / xgc_avg_3 features for BOTH
historical and live data.

IMPORTANT: historical rows are NEVER used for prediction, only concatenated
into the training set. Historical player_ids are offset well above the
range live FPL player_ids ever use, so they can never accidentally collide
with (and corrupt the rolling-form calculation for) a real current player.
"""

import io
import logging
import requests
import pandas as pd

from config import HISTORICAL_SEASONS, HISTORICAL_DATA_BASE_URL, RAW_DIR, FALLBACK_AGE

logger = logging.getLogger(__name__)

POSITION_TO_ELEMENT_TYPE = {"GK": 1, "GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}

# Historical synthetic player_ids live here — live FPL player_ids are small
# integers (well under 10,000), so this range can never collide with them.
PLAYER_ID_BASE = 1_000_000


def _season_cache_path(season: str, name: str):
    return RAW_DIR / f"historical_{season}_{name}.csv"


def _fetch_csv_text(url: str, cache_path) -> str:
    if cache_path.exists():
        return cache_path.read_text()
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    cache_path.write_text(resp.text)
    return resp.text


def _team_strength_lookups(teams_df: pd.DataFrame):
    """Returns (by_id, by_name) strength lookup dicts for one season's teams.csv."""
    by_id, by_name = {}, {}
    for _, t in teams_df.iterrows():
        entry = {
            "attack": (t["strength_attack_home"] + t["strength_attack_away"]) / 2,
            "defence": (t["strength_defence_home"] + t["strength_defence_away"]) / 2,
        }
        by_id[t["id"]] = entry
        by_name[t["name"]] = entry
    return by_id, by_name


def fetch_season(season: str, season_index: int):
    """Downloads one completed season's per-gameweek player data + team
    strength ratings, returns a DataFrame in the SAME raw schema as
    build_gameweek_history_df() — ready for add_rolling_features(). Returns
    None if the season isn't available.
    """
    gw_url = f"{HISTORICAL_DATA_BASE_URL}/{season}/gws/merged_gw.csv"
    teams_url = f"{HISTORICAL_DATA_BASE_URL}/{season}/teams.csv"

    try:
        gw_text = _fetch_csv_text(gw_url, _season_cache_path(season, "merged_gw"))
        teams_text = _fetch_csv_text(teams_url, _season_cache_path(season, "teams"))
    except requests.RequestException as e:
        logger.warning("Historical season %s unavailable, skipping: %s", season, e)
        return None

    gw_df = pd.read_csv(io.StringIO(gw_text))
    teams_df = pd.read_csv(io.StringIO(teams_text))
    if gw_df.empty or teams_df.empty:
        return None

    id_strength, name_strength = _team_strength_lookups(teams_df)

    # Unique per (season, element) — offset so it never collides with a
    # live FPL player_id or with another season's ids in this same load.
    codes, _ = pd.factorize(gw_df["element"].astype(str))
    gw_df["player_id"] = codes + PLAYER_ID_BASE + season_index * 100_000

    out = pd.DataFrame({
        "player_id": gw_df["player_id"],
        "web_name": gw_df["name"],
        "element_type": gw_df["position"].map(POSITION_TO_ELEMENT_TYPE).fillna(3).astype(int),
        "round": gw_df["GW"],
        "minutes": gw_df["minutes"].fillna(0),
        "total_points": gw_df["total_points"].fillna(0),
        "ict_index": pd.to_numeric(gw_df["ict_index"], errors="coerce").fillna(0),
        "influence": pd.to_numeric(gw_df["influence"], errors="coerce").fillna(0),
        "creativity": pd.to_numeric(gw_df["creativity"], errors="coerce").fillna(0),
        "threat": pd.to_numeric(gw_df["threat"], errors="coerce").fillna(0),
        "was_home": gw_df["was_home"].astype(bool).astype(int),
        "now_cost": gw_df["value"].fillna(50),
        "kickoff_time": pd.to_datetime(gw_df["kickoff_time"], errors="coerce", utc=True).dt.tz_localize(None),
        "age": FALLBACK_AGE,  # birth dates aren't available in this dataset
        "expected_goal_involvements": pd.to_numeric(
            gw_df["expected_goal_involvements"], errors="coerce"
        ).fillna(0) if "expected_goal_involvements" in gw_df.columns else 0.0,
        "expected_goals_conceded": pd.to_numeric(
            gw_df["expected_goals_conceded"], errors="coerce"
        ).fillna(0) if "expected_goals_conceded" in gw_df.columns else 0.0,
    })

    out["team_strength_attack"] = gw_df["team"].map(lambda t: name_strength.get(t, {}).get("attack", 1100))
    out["team_strength_defence"] = gw_df["team"].map(lambda t: name_strength.get(t, {}).get("defence", 1100))
    out["opp_strength_attack"] = gw_df["opponent_team"].map(lambda o: id_strength.get(o, {}).get("attack", 1100))
    out["opp_strength_defence"] = gw_df["opponent_team"].map(lambda o: id_strength.get(o, {}).get("defence", 1100))

    return out


def build_historical_training_df(seasons=None) -> pd.DataFrame:
    """Fetches every configured historical season and concatenates them into
    one raw history-shaped DataFrame, ready for add_rolling_features().
    Skips any season that fails to fetch rather than aborting the whole run
    — multi-season data is an enhancement, not a hard dependency.
    """
    seasons = seasons or HISTORICAL_SEASONS
    frames = []
    for i, season in enumerate(seasons):
        logger.info("Fetching historical season %s...", season)
        df = fetch_season(season, season_index=i)
        if df is not None and not df.empty:
            frames.append(df)
            logger.info("  %s: %d rows", season, len(df))

    if not frames:
        logger.warning("No historical seasons could be fetched — training on current season data only.")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined.sort_values(["player_id", "round"], inplace=True)
    return combined