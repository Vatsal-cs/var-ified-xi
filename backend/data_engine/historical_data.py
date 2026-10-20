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
from data_engine import odds_data, setpiece_data, team_form

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

    # A player can't appear twice in one match, but the 2025-26 export lists
    # ten fringe players twice for the same fixture (identical rows, 27
    # points between them). Left in, they read as a double gameweek and
    # their points are counted twice.
    if "fixture" in gw_df.columns:
        gw_df = gw_df.drop_duplicates(["element", "fixture"]).reset_index(drop=True)

    id_strength, name_strength = _team_strength_lookups(teams_df)
    name_to_id = dict(zip(teams_df["name"], teams_df["id"]))
    if config.LAGGED_TEAM_RATINGS or season in config.LAGGED_TEAM_RATINGS_SEASONS:
        id_strength, name_strength = _lagged_strengths(season, teams_df)

    # Unique per (season, element) — offset so it never collides with a
    # live FPL player_id or with another season's ids in this same load.
    codes, _ = pd.factorize(gw_df["element"].astype(str))
    gw_df["player_id"] = codes + PLAYER_ID_BASE + season_index * 100_000

    out = pd.DataFrame({
        "player_id": gw_df["player_id"],
        # The official FPL id that season, kept so per-gameweek side data
        # keyed on it (availability, set pieces) can be joined later.
        "element": gw_df["element"].astype(int),
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
        # Share of managers owning this player that gameweek. Not a model
        # feature — it's the field's position, used to work out how much of a
        # score is rank-GAINING rather than merely large. Normalised by the
        # implied manager count (total selections / 15 squad slots), which
        # tracks the real figure closely: it puts Haaland at 69% in 2025-26
        # GW10, matching what FPL published.
        "ownership": _ownership_share(gw_df),
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
    # Match identity, for team-level form (team_form.py).
    out["fixture"] = gw_df["fixture"] if "fixture" in gw_df.columns else 0
    out["opponent_team"] = (pd.to_numeric(gw_df["opponent_team"], errors="coerce").fillna(0).astype(int)
                            + HISTORICAL_TEAM_ID_BASE + season_index * 100)

    out["team_strength_attack"] = gw_df["team"].map(lambda t: name_strength.get(t, {}).get("attack", 1100))
    out["team_strength_defence"] = gw_df["team"].map(lambda t: name_strength.get(t, {}).get("defence", 1100))
    out["opp_strength_attack"] = gw_df["opponent_team"].map(lambda o: id_strength.get(o, {}).get("attack", 1100))
    out["opp_strength_defence"] = gw_df["opponent_team"].map(lambda o: id_strength.get(o, {}).get("defence", 1100))

    _attach_odds_features(out, gw_df, season)
    _attach_setpiece_features(out, gw_df, season)
    if config.TEAM_FORM:
        offset = HISTORICAL_TEAM_ID_BASE + season_index * 100
        names = {int(r["id"]) + offset: r["name"] for _, r in teams_df.iterrows()}
        if config.TEAM_FORM_SOURCE == "odds":
            canon = {tid: odds_data.canonical_team(n) for tid, n in names.items()}
            start = team_form.priors(final_market_form(_previous_season(season)), canon)
        else:
            start = team_form.priors(final_team_form(_previous_season(season)), names)
        team_form.SEASON_START[season] = start
        team_form.attach(out, start)
    if config.OWNERSHIP_FEATURE:
        out["selected_by_percent"] = out["ownership"].astype(float) * 100.0

    return out


def _lagged_strengths(season: str, teams_df: pd.DataFrame):
    """(by id, by name) ratings for `season` taken from the season before —
    as the live model must do when FPL publishes none. A club that wasn't in
    the league then is rated like the clubs that went down."""
    prev = _previous_season(season)
    prev_df = pd.read_csv(io.StringIO(_fetch_csv_text(
        f"{HISTORICAL_DATA_BASE_URL}/{prev}/teams.csv", _season_cache_path(prev, "teams"))))
    _, prev_by_name = _team_strength_lookups(prev_df)
    gone = [v for n, v in prev_by_name.items() if n not in set(teams_df["name"])] or list(prev_by_name.values())
    promoted = {k: sum(v[k] for v in gone) / len(gone) for k in ("attack", "defence")}
    by_name = {n: dict(prev_by_name.get(n, promoted)) for n in teams_df["name"]}
    by_id = {int(i): by_name[n] for i, n in zip(teams_df["id"], teams_df["name"])}
    return by_id, by_name


def _previous_season(season: str) -> str:
    """'2024-25' -> '2023-24'."""
    start = int(season[:4]) - 1
    return f"{start}-{str(start + 1)[2:]}"


def final_team_form(season: str) -> dict:
    """{club name: (attack, defence)} at the end of a completed season, from
    the archive — the prior for the season after. None if that season isn't
    available or carries no xG (the archive's xG begins in 2022-23)."""
    try:
        gw_df = pd.read_csv(io.StringIO(_fetch_csv_text(
            f"{HISTORICAL_DATA_BASE_URL}/{season}/gws/merged_gw.csv",
            _season_cache_path(season, "merged_gw"))), low_memory=False)
        teams_df = pd.read_csv(io.StringIO(_fetch_csv_text(
            f"{HISTORICAL_DATA_BASE_URL}/{season}/teams.csv",
            _season_cache_path(season, "teams"))))
    except requests.RequestException:
        return None
    need = {"team", "opponent_team", "fixture", "kickoff_time", "expected_goals"}
    if not need <= set(gw_df.columns) or pd.to_numeric(gw_df["expected_goals"], errors="coerce").fillna(0).sum() == 0:
        return None
    id_by_name = dict(zip(teams_df["name"], teams_df["id"]))
    rows = pd.DataFrame({
        "team": gw_df["team"].map(id_by_name),
        "opponent_team": pd.to_numeric(gw_df["opponent_team"], errors="coerce"),
        "fixture": gw_df["fixture"],
        "kickoff_time": pd.to_datetime(gw_df["kickoff_time"], errors="coerce", utc=True),
        "expected_goals": pd.to_numeric(gw_df["expected_goals"], errors="coerce").fillna(0),
    }).dropna(subset=["team", "opponent_team"])
    return team_form.final_by_name(rows, dict(zip(teams_df["id"], teams_df["name"])))


def final_market_form(season: str) -> dict:
    """{canonical club name: (attack, defence)} at the end of a season, from
    the goals betting odds expected in each of its matches — the prior for
    the season after when team form comes from odds. None if unavailable."""
    odds = odds_data.fetch_season_odds(season)
    if odds.empty:
        return None
    rows = []
    for i, m in enumerate(odds.itertuples()):
        rows.append((m.home, i, m.date, m.home_xg, m.away_xg))
        rows.append((m.away, i, m.date, m.away_xg, m.home_xg))
    matches = (pd.DataFrame(rows, columns=["team", "fixture", "kickoff_time", "xg_for", "xg_against"])
                 .sort_values(["kickoff_time", "fixture"]))
    _, now = team_form.ratings(matches, {})
    return now


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


def _ownership_share(gw_df: pd.DataFrame) -> pd.Series:
    """Fraction of managers owning each player, per gameweek.

    The archive records `selected` as a raw manager count, and the total
    entrant count isn't published alongside it — but every manager holds
    exactly 15 players, so the selections in a gameweek sum to 15x the field.
    """
    if "selected" not in gw_df.columns:
        return pd.Series(0.0, index=gw_df.index)
    selected = pd.to_numeric(gw_df["selected"], errors="coerce").fillna(0.0)
    managers = selected.groupby(gw_df["GW"]).transform("sum") / 15.0
    return (selected / managers.replace(0, pd.NA)).fillna(0.0).clip(0, 1)


def _attach_setpiece_features(out: pd.DataFrame, gw_df: pd.DataFrame, season: str) -> None:
    """Joins per-gameweek set-piece duty onto each player row by (element,
    gameweek). Rows with no match — a whole season this dataset doesn't cover,
    or simply a player who takes nothing — get zero, which is what "no duty"
    means in this encoding.

    The snapshot labelled t is taken after t is played (see
    availability_data), so gameweek t reads snapshot t - 1: the duties known
    at its deadline. Keying on t itself let a row see a penalty order revised
    after its own match. The set-piece variant was measured (and rejected)
    under that leaky key; a leak can only flatter a feature, so the verdict
    stands.
    """
    for col, neutral in setpiece_data.SETPIECE_NEUTRAL.items():
        out[col] = neutral
    if not config.ATTACH_SETPIECE:
        return  # see config.ATTACH_SETPIECE

    sp = setpiece_data.fetch_season_setpieces(season)
    if sp.empty:
        return

    lut = sp.set_index(["element", "round"])[setpiece_data.SETPIECE_FEATURE_COLUMNS]
    keys = pd.MultiIndex.from_arrays([
        gw_df["element"].astype(int), gw_df["GW"].astype(int) - 1
    ])
    joined = lut.reindex(keys).fillna(0.0)
    for col in setpiece_data.SETPIECE_FEATURE_COLUMNS:
        out[col] = joined[col].to_numpy()

    duties = int((joined.sum(axis=1) > 0).sum())
    logger.info("Set-piece join %s: %d / %d player-rows carry a duty",
                season, duties, len(out))


def fallback_team_strengths(teams: list, season: str = None) -> dict:
    """Team id -> {attack, defence} from the most recent completed season's
    published ratings, for a season in which FPL publishes none.

    Matched by club name. A club that wasn't in the league last season (just
    promoted) is rated as the average of last season's clubs that are no
    longer in it — the relegated sides — which is where promoted clubs
    usually land. Returns {} if last season's ratings can't be had.
    """
    season = season or HISTORICAL_SEASONS[-1]
    try:
        text = _fetch_csv_text(f"{HISTORICAL_DATA_BASE_URL}/{season}/teams.csv",
                               _season_cache_path(season, "teams"))
    except requests.RequestException as e:
        logger.warning("No fallback team strengths (%s): %s", season, e)
        return {}
    last = pd.read_csv(io.StringIO(text))
    rating = {
        row["name"]: {
            "attack": (row["strength_attack_home"] + row["strength_attack_away"]) / 2,
            "defence": (row["strength_defence_home"] + row["strength_defence_away"]) / 2,
        }
        for _, row in last.iterrows()
    }
    current = {t["name"] for t in teams}
    gone = [v for name, v in rating.items() if name not in current] or list(rating.values())
    promoted = {k: sum(v[k] for v in gone) / len(gone) for k in ("attack", "defence")}

    out, missing = {}, []
    for t in teams:
        if t["name"] in rating:
            out[t["id"]] = dict(rating[t["name"]])
        else:
            out[t["id"]] = dict(promoted)
            missing.append(t["name"])
    logger.warning("FPL publishes no team strengths this season; using %s ratings%s.",
                   season, f" (rated like last season's relegated clubs: {', '.join(missing)})"
                   if missing else "")
    return out


def attach_other_matches(df: pd.DataFrame, season: str, season_index: int) -> None:
    """Adds other_matches' inputs to one archived season, in place: names
    are the archive's full names, clubs its own team list."""
    from data_engine import other_matches
    teams = pd.read_csv(config.RAW_DIR / f"historical_{season}_teams.csv")
    offset = HISTORICAL_TEAM_ID_BASE + season_index * 100
    clubs = {offset + int(i): n for i, n in zip(teams["id"], teams["name"])}
    try:
        other_matches.attach(df, season, dict(zip(df["player_id"], df["web_name"])), clubs)
    except Exception as e:                           # an outage leaves neutral values
        logger.warning("Other matches for %s unavailable (%s); neutral values used", season, e)
        for col, v in other_matches.NEUTRAL.items():
            df[col] = v


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
            if config.OTHER_MATCHES:
                attach_other_matches(df, season, i)
            frames.append(df)
            logger.info("  %s: %d rows", season, len(df))

    if not frames:
        logger.warning("No historical seasons could be fetched — training on current season data only.")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined.sort_values(["player_id", "round"], inplace=True)
    return combined