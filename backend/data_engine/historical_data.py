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

import config
from config import HISTORICAL_SEASONS, HISTORICAL_DATA_BASE_URL, RAW_DIR, FALLBACK_AGE
from data_engine import odds_data

logger = logging.getLogger(__name__)

POSITION_TO_ELEMENT_TYPE = {"GK": 1, "GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}

# Historical synthetic player_ids live here — live FPL player_ids are small
# integers (well under 10,000), so this range can never collide with them.
PLAYER_ID_BASE = 1_000_000

# Same idea for club ids: live FPL team ids are 1-20, so historical clubs are
# offset far above that range.
HISTORICAL_TEAM_ID_BASE = 10_000


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


def _numeric(gw_df: pd.DataFrame, col: str, default: float = 0.0):
    """Safely pulls a numeric column that may not exist in every season's
    export (FPL adds new stats over time — e.g. defensive_contribution only
    exists from 2025-26, when the scoring rule was introduced).
    """
    if col not in gw_df.columns:
        return default
    return pd.to_numeric(gw_df[col], errors="coerce").fillna(default)


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
    name_to_id = dict(zip(teams_df["name"], teams_df["id"]))

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
        "ict_index": _numeric(gw_df, "ict_index"),
        "influence": _numeric(gw_df, "influence"),
        "creativity": _numeric(gw_df, "creativity"),
        "threat": _numeric(gw_df, "threat"),
        "was_home": gw_df["was_home"].astype(bool).astype(int),
        "now_cost": gw_df["value"].fillna(50),
        "kickoff_time": pd.to_datetime(gw_df["kickoff_time"], errors="coerce", utc=True).dt.tz_localize(None),
        "age": FALLBACK_AGE,  # birth dates aren't available in this dataset
        "expected_goal_involvements": _numeric(gw_df, "expected_goal_involvements"),
        "expected_goals_conceded": _numeric(gw_df, "expected_goals_conceded"),
        # Bonus-point proxy and start-share signal — present in every season.
        "bps": _numeric(gw_df, "bps"),
        "bonus": _numeric(gw_df, "bonus"),
        "starts": _numeric(gw_df, "starts"),
        # Split xG/xA carry more signal than the combined involvement figure:
        # a striker's xG and a playmaker's xA decay differently.
        "expected_goals": _numeric(gw_df, "expected_goals"),
        "expected_assists": _numeric(gw_df, "expected_assists"),
        # Goalkeeper / defender scoring inputs.
        "saves": _numeric(gw_df, "saves"),
        "clean_sheets": _numeric(gw_df, "clean_sheets"),
        "goals_conceded": _numeric(gw_df, "goals_conceded"),
        # FPL's own published expected-points figure. Never a model feature
        # (it's a forecast, not an observation) and no longer used as a
        # benchmark either: a squad built from these values scores ~99 points
        # per gameweek against ~148 for perfect hindsight, which no
        # pre-deadline forecast could manage. The archive evidently records
        # them after lineups are known. Kept only so the finding stays
        # checkable — see backtest.py's module docstring.
        "fpl_xp": _numeric(gw_df, "xP"),
        # Defensive-contribution scoring, introduced in 2025-26. Older
        # seasons return 0.0 rather than failing.
        "defensive_contribution": _numeric(gw_df, "defensive_contribution"),
    })

    # Real club identity, needed by the optimizer's max-3-per-club constraint
    # when backtesting on historical seasons. Offset into a private range so
    # a historical club id can never be confused with a live FPL team id
    # (1-20) after these rows are concatenated into the training set.
    out["team"] = (
        gw_df["team"].map(lambda t: name_to_id.get(t, 0)).fillna(0).astype(int)
        + HISTORICAL_TEAM_ID_BASE
        + season_index * 100
    )

    out["team_strength_attack"] = gw_df["team"].map(lambda t: name_strength.get(t, {}).get("attack", 1100))
    out["team_strength_defence"] = gw_df["team"].map(lambda t: name_strength.get(t, {}).get("defence", 1100))
    out["opp_strength_attack"] = gw_df["opponent_team"].map(lambda o: id_strength.get(o, {}).get("attack", 1100))
    out["opp_strength_defence"] = gw_df["opponent_team"].map(lambda o: id_strength.get(o, {}).get("defence", 1100))

    _attach_odds_features(out, gw_df, season)

    return out


def _attach_odds_features(out: pd.DataFrame, gw_df: pd.DataFrame, season: str) -> None:
    """Joins betting-odds-derived fixture expectations onto each player row by
    (match date, the player's own team). Missing matches get league-median
    neutrals so the columns are never NaN.
    """
    for col, neutral in odds_data.ODDS_NEUTRAL.items():
        out[col] = neutral
    if not config.ATTACH_ODDS:
        return  # rejected feature — see config.ATTACH_ODDS
    odds_df = odds_data.fetch_season_odds(season)
    if odds_df.empty:
        return

    lut = odds_data.per_team_lookup(odds_df)
    match_date = pd.to_datetime(gw_df["kickoff_time"], errors="coerce", utc=True).dt.tz_localize(None).dt.date
    team_canon = gw_df["team"].map(odds_data.canonical_team)

    matched = 0
    for col in odds_data.ODDS_FEATURE_COLUMNS:
        vals = []
        for d, t in zip(match_date, team_canon):
            hit = lut.get((d, t))
            vals.append(hit[col] if hit else odds_data.ODDS_NEUTRAL[col])
        out[col] = vals
    matched = sum(1 for d, t in zip(match_date, team_canon) if (d, t) in lut)
    logger.info("Odds join %s: %d / %d player-rows matched", season, matched, len(out))


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