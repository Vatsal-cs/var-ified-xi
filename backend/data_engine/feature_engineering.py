"""
File: feature_engineering.py
Path: var-ified-xi/backend/data_engine/feature_engineering.py

Turns raw FPL API responses into a flat, per-player-per-gameweek DataFrame
with rolling-form features. Used both to build the XGBoost TRAINING set
(historical gameweeks -> actual points scored) and the PREDICTION set
(most recent form -> features for the upcoming gameweek).

v2 changes:
  - Prediction rows now use the player's NEXT unplayed fixture (opponent,
    home/away, difficulty) instead of their LAST played match. The
    previous version silently used last week's opponent to predict next
    week's points, which is wrong every single week.
  - Added days_since_last_match (rest/congestion proxy) and age, computed
    for both training and prediction rows so the distributions match.
  - Predictions for players with no fixture next gameweek (blanks) are
    flagged via has_fixture=False so the caller can zero them out.

v2.1 fix:
  - Distinguishes a genuine isolated blank gameweek (a small minority of
    players have no fixture while most do) from FPL simply not having
    published next season's fixtures yet (during the close season, EVERY
    player's fixtures array is empty). The first case should zero those
    players' predictions; the second should fall back to last-known-match
    context instead of collapsing the entire player pool to zero. See
    'fixtures_published' in the returned DataFrame.
"""

import logging
from datetime import date, datetime

import pandas as pd
import numpy as np

from config import (
    ROLLING_WINDOWS,
    FALLBACK_AGE,
    HORIZON_DECAY,
    FORM_SHRINKAGE_GAMES,
)

logger = logging.getLogger(__name__)

# If fewer than this fraction of players have any upcoming fixture at all,
# treat it as "fixtures not published yet" rather than "genuine blanks".
# A real blank gameweek (e.g. FA Cup replay clashes) affects at most a
# couple of clubs — nowhere near half the league.
FIXTURES_PUBLISHED_THRESHOLD = 0.5

# Every rolling-average feature the model can see, declared once.
#   (source column, output prefix, windows)
# Each is computed per player as shift(1).rolling(w).mean() — the shift is
# what keeps a row's features strictly in its own past. A source column that
# a given season's data doesn't carry is filled with 0.0 rather than failing,
# which is what lets one spec serve both the live API and the historical
# archive without either side drifting out of schema.
ROLLING_FEATURE_SPEC = [
    ("minutes", "minutes_avg", ROLLING_WINDOWS),
    ("total_points", "points_avg", ROLLING_WINDOWS),
    ("ict_index", "ict_index_avg", ROLLING_WINDOWS),
    ("influence", "influence_avg", [3]),
    ("creativity", "creativity_avg", [3]),
    ("threat", "threat_avg", [3]),
    # Underlying chance quality — a better forward-looking signal than ICT,
    # which is partly a descriptive scoring of what already happened.
    ("expected_goal_involvements", "xgi_avg", [3]),
    ("expected_goals_conceded", "xgc_avg", [3]),
    ("expected_goals", "xg_avg", [3, 5]),
    ("expected_assists", "xa_avg", [3, 5]),
    # Bonus points are ~10% of all FPL scoring and highly persistent — BPS is
    # the underlying score the bonus is awarded from.
    ("bps", "bps_avg", [3, 5]),
    ("bonus", "bonus_avg", [5]),
    # Started-or-not is a far sharper rotation signal than minutes alone: 45
    # minutes off the bench and 45 before a red card look identical otherwise.
    ("starts", "starts_avg", [3, 5]),
    # Defensive-contribution scoring, new in 2025-26.
    ("defensive_contribution", "dc_avg", [3, 5]),
    # Goalkeeper and defender scoring inputs.
    ("saves", "saves_avg", [3]),
    ("clean_sheets", "cs_avg", [5]),
    ("goals_conceded", "gc_avg", [3]),
]


def _team_strength_lookup(bootstrap: dict) -> dict:
    """Map team id -> dict of attack/defence strength ratings from bootstrap-static."""
    lookup = {}
    for t in bootstrap["teams"]:
        lookup[t["id"]] = {
            "attack": (t["strength_attack_home"] + t["strength_attack_away"]) / 2,
            "defence": (t["strength_defence_home"] + t["strength_defence_away"]) / 2,
        }
    return lookup


def _parse_kickoff(kickoff_str):
    if not kickoff_str:
        return None
    try:
        return pd.Timestamp(kickoff_str).tz_localize(None)
    except (ValueError, TypeError):
        return None


def _player_age(birth_date_str) -> float:
    """Age in years as of today. Returns NaN (filled to 0 later) if the API
    doesn't have a birth date for this player (happens for some new signings).
    """
    if not birth_date_str:
        return np.nan
    try:
        b = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        today = date.today()
        return (today - b).days / 365.25
    except (ValueError, TypeError):
        return np.nan



def _positional_priors(df: pd.DataFrame, source: str) -> pd.Series:
    """Typical per-match value of a stat for each position.

    Used as the fallback belief about a player we have barely seen. A
    defender who has played once is much more likely to be an ordinary
    defender than the best in the league.
    """
    if "element_type" not in df.columns:
        return pd.Series(dtype=float)
    return df.groupby("element_type")[source].mean()


def _shrink(observed: pd.Series, counts: pd.Series, priors: pd.Series,
            element_type: pd.Series, k: float) -> pd.Series:
    """Pulls a rolling average toward the positional prior when it rests on
    very few matches.

    A three-game average built from one game is not a three-game average —
    it is one result wearing a trustworthy label. In the opening weeks that
    makes every high scorer look like a permanent star: after gameweek 1 of
    2026-27 the squad picked 31% of players who scored 11+ and 0.7% of those
    who scored 0-1, which is chasing noise, not form.

    The standard remedy is to blend the observation with a prior in
    proportion to how much evidence there is:

        shrunk = (n * observed + k * prior) / (n + k)

    With one match played the estimate sits mostly on the prior; by the time
    k matches have been played the observation dominates. k is
    FORM_SHRINKAGE_GAMES in config.
    """
    if k <= 0:
        return observed
    prior_values = element_type.map(priors)
    prior_values = prior_values.fillna(observed.mean() if len(observed) else 0.0)
    n = counts.fillna(0)
    return (n * observed.fillna(0) + k * prior_values) / (n + k)


def build_gameweek_history_df(bootstrap: dict, player_histories: dict,
                              fixtures: list = None) -> pd.DataFrame:
    """Flattens every player's gameweek-by-gameweek 'history' entries into one
    long DataFrame: one row = one player's performance in one past gameweek.

    fixtures: the season fixture list, used to keep only rows from matches
    that have actually been played. Once a gameweek kicks off, FPL's API
    pre-creates a zero-filled history row for every player whose match is
    still to come — run the pipeline mid-gameweek without this filter and
    every such player appears to have just been benched for a duck, which
    (observed on 2026-08-29, mid-GW2) halves their play probability and
    throws the premiums out of the squad. Without a fixtures list, rows
    whose kickoff is still in the future are dropped as a fallback.
    """
    team_strength = _team_strength_lookup(bootstrap)
    players_meta = {p["id"]: p for p in bootstrap["elements"]}

    played_fixtures = None
    if fixtures is not None:
        played_fixtures = {
            f["id"] for f in fixtures
            if f.get("finished") or f.get("finished_provisional")
        }
    now = pd.Timestamp.utcnow().tz_localize(None)

    rows = []
    skipped = 0
    for pid, summary in player_histories.items():
        meta = players_meta.get(pid)
        if meta is None:
            continue
        for gw in summary.get("history", []):
            if played_fixtures is not None:
                if gw.get("fixture") not in played_fixtures:
                    skipped += 1
                    continue
            else:
                ko = _parse_kickoff(gw.get("kickoff_time"))
                if ko is not None and ko > now:
                    skipped += 1
                    continue
            opp_id = gw.get("opponent_team")
            rows.append({
                "player_id": pid,
                "web_name": meta.get("web_name"),
                "element_type": meta.get("element_type"),
                "team": meta.get("team"),
                "round": gw.get("round"),
                "minutes": gw.get("minutes", 0),
                "total_points": gw.get("total_points", 0),
                "ict_index": float(gw.get("ict_index", 0) or 0),
                "influence": float(gw.get("influence", 0) or 0),
                "creativity": float(gw.get("creativity", 0) or 0),
                "threat": float(gw.get("threat", 0) or 0),
                "was_home": int(gw.get("was_home", False)),
                "now_cost": gw.get("value", meta.get("now_cost", 0)),
                "opponent_team": opp_id,
                "kickoff_time": _parse_kickoff(gw.get("kickoff_time")),
                "team_strength_attack": team_strength.get(meta.get("team"), {}).get("attack", 1100),
                "team_strength_defence": team_strength.get(meta.get("team"), {}).get("defence", 1100),
                "opp_strength_attack": team_strength.get(opp_id, {}).get("attack", 1100),
                "opp_strength_defence": team_strength.get(opp_id, {}).get("defence", 1100),
                "age": _player_age(meta.get("birth_date")),
                "expected_goal_involvements": float(gw.get("expected_goal_involvements", 0) or 0),
                "expected_goals_conceded": float(gw.get("expected_goals_conceded", 0) or 0),
                # Every field below also exists in the vaastav archive's
                # merged_gw export, so training and prediction rows carry
                # identical schemas — no train/predict skew.
                "expected_goals": float(gw.get("expected_goals", 0) or 0),
                "expected_assists": float(gw.get("expected_assists", 0) or 0),
                "bps": float(gw.get("bps", 0) or 0),
                "bonus": float(gw.get("bonus", 0) or 0),
                "starts": float(gw.get("starts", 0) or 0),
                "defensive_contribution": float(gw.get("defensive_contribution", 0) or 0),
                "saves": float(gw.get("saves", 0) or 0),
                "clean_sheets": float(gw.get("clean_sheets", 0) or 0),
                "goals_conceded": float(gw.get("goals_conceded", 0) or 0),
            })

    if skipped:
        logger.info("Dropped %d history rows for matches not yet played "
                    "(mid-gameweek run).", skipped)

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("No gameweek history rows built — check player_histories input.")
    df.sort_values(["player_id", "round"], inplace=True)
    return df


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Adds rolling-average form features per player, shifted by 1 gameweek
    so we never leak the current/target gameweek's own stats into training.
    Also adds days_since_last_match, a rest/fixture-congestion proxy.
    """
    df = df.copy()
    grp = df.groupby("player_id", group_keys=False)

    for source, prefix, windows in ROLLING_FEATURE_SPEC:
        priors = _positional_priors(df, source) if source in df.columns else None
        for w in windows:
            name = f"{prefix}_{w}"
            if source in df.columns:
                df[name] = grp[source].apply(
                    lambda s: s.shift(1).rolling(w, min_periods=1).mean()
                )
                counts = grp[source].apply(
                    lambda s: s.shift(1).rolling(w, min_periods=1).count()
                )
                df[name] = _shrink(df[name], counts, priors,
                                   df["element_type"], FORM_SHRINKAGE_GAMES)
            else:
                # A stat FPL only started publishing in a later season (e.g.
                # defensive_contribution, new in 2025-26). Zero is the honest
                # value: the scoring rule didn't exist, so it earned nothing.
                df[name] = 0.0

    # How many matches this player has actually played. Lets the model itself
    # learn how far to trust the form features, rather than treating a
    # one-game average and a twenty-game average as equally solid.
    df["matches_played"] = grp["minutes"].apply(lambda s: s.shift(1).expanding().count())

    # 'form' as FPL defines it loosely: average points over last 5 played gameweeks
    df["form"] = df["points_avg_5"]

    df["fixture_difficulty"] = (df["opp_strength_defence"] - df["team_strength_attack"]) / 100.0

    # Rest days between consecutive PL matches for the same player. Note:
    # FPL's history endpoint only covers Premier League gameweek fixtures —
    # it has no visibility into cup or European matches, so this is a
    # partial congestion signal (PL scheduling gaps only), not true fatigue
    # tracking. Still meaningfully better than nothing.
    df["days_since_last_match"] = grp["kickoff_time"].apply(
        lambda s: s.diff().dt.days
    )

    # Fill age's missing values with a neutral fallback BEFORE the generic
    # fillna(0) below — age=0 would read as an implausible outlier the
    # model could latch onto, whereas age=26 (~league average) is honest
    # about "we don't know" without distorting the feature's distribution.
    if "age" in df.columns:
        df["age"] = df["age"].fillna(FALLBACK_AGE)

    df.fillna(0, inplace=True)
    return df


def latest_form_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """One row per player holding their form going INTO the next fixture.

    add_rolling_features() shifts every window by one gameweek, because a
    training row must never see its own match. A prediction row is the
    opposite case: the match hasn't been played yet, so the most recent
    completed match is legitimate input, not leakage — and excluding it means
    every prediction is made on week-old form. In the opening weeks of a
    season that is fatal, because shifting away the only gameweek played
    leaves every feature at zero.

    So the windows here are computed UNSHIFTED and read off the last played
    row. The semantics then match training exactly: a training row for
    gameweek t averages matches [t-w, t-1]; this averages the last w played
    matches, which are precisely the w matches before the fixture being
    predicted.
    """
    df = df.sort_values(["player_id", "round"])
    grp = df.groupby("player_id", group_keys=False)

    out = df.copy()
    for source, prefix, windows in ROLLING_FEATURE_SPEC:
        priors = _positional_priors(df, source) if source in df.columns else None
        for w in windows:
            name = f"{prefix}_{w}"
            if source in df.columns:
                out[name] = grp[source].apply(
                    lambda s: s.rolling(w, min_periods=1).mean()
                )
                counts = grp[source].apply(
                    lambda s: s.rolling(w, min_periods=1).count()
                )
                out[name] = _shrink(out[name], counts, priors,
                                    out["element_type"], FORM_SHRINKAGE_GAMES)
            else:
                out[name] = 0.0

    out["matches_played"] = grp["minutes"].apply(lambda s: s.expanding().count())

    out["form"] = out["points_avg_5"]
    if "age" in out.columns:
        out["age"] = out["age"].fillna(FALLBACK_AGE)
    out = out.fillna(0)
    return out.groupby("player_id", as_index=False).tail(1).copy()


def aggregate_horizon(predictions_df: pd.DataFrame, decay: float = HORIZON_DECAY) -> pd.DataFrame:
    """Collapses (player, fixture) prediction rows into one row per player.

    Adds three columns the optimizer and the dashboard need:
      predicted_points — expected points in the NEXT gameweek alone, summed
                         across both matches if it's a double.
      horizon_points   — decay-weighted sum across the whole horizon. This is
                         what the optimizer maximizes, so a player is judged
                         on the run of fixtures you'd actually hold him for.
      xp_by_gw         — {gameweek: expected points}, for the dashboard's
                         fixture strip.
    """
    df = predictions_df.copy()
    if "gw" not in df.columns:
        # Single-gameweek mode (or the close-season fallback): nothing to fold.
        df["horizon_points"] = df["predicted_points"]
        df["xp_by_gw"] = [{} for _ in range(len(df))]
        return df

    first_gw = df["gw"].min()

    # Sum within a gameweek first — that is what makes a double gameweek
    # score as two matches rather than being averaged away.
    per_gw = df.groupby(["player_id", "gw"], as_index=False)["predicted_points"].sum()
    per_gw["weight"] = decay ** (per_gw["gw"] - first_gw)
    per_gw["weighted"] = per_gw["predicted_points"] * per_gw["weight"]

    horizon = per_gw.groupby("player_id")["weighted"].sum()
    next_gw = (
        per_gw[per_gw["gw"] == first_gw].set_index("player_id")["predicted_points"]
    )
    xp_by_gw = per_gw.groupby("player_id").apply(
        lambda g: {int(gw): round(float(p), 2) for gw, p in zip(g["gw"], g["predicted_points"])},
        include_groups=False,
    )

    out = df.drop_duplicates("player_id").set_index("player_id")
    out["predicted_points"] = next_gw.reindex(out.index).fillna(0.0)
    out["horizon_points"] = horizon.reindex(out.index).fillna(0.0).round(2)
    out["xp_by_gw"] = xp_by_gw.reindex(out.index)
    out["xp_by_gw"] = out["xp_by_gw"].apply(lambda v: v if isinstance(v, dict) else {})
    return out.reset_index()


def build_training_set(df_with_rolling: pd.DataFrame) -> pd.DataFrame:
    """Every past gameweek row, used to train the model.

    This deliberately keeps players with no recent minutes. An earlier version
    dropped them, on the reasoning that chronic non-players are noise — but
    the stage-1 model's entire job is judging whether someone will play, and
    it cannot learn that from a sample containing only players who do. With
    them filtered out the model concluded nearly everyone starts and
    over-predicted every squad by roughly a fifth.

    The stage-2 quality model still wants the cleaner population, and applies
    that filter itself (see train_model._fit_bundle's quality_filter).
    Backtested over 2024-25 and 2025-26: mean absolute error fell from ~1.16
    to ~1.05 points with no loss of simulated points.
    """
    train_df = df_with_rolling.copy()
    if "selected_by_percent" not in train_df.columns:
        train_df["selected_by_percent"] = 0.0
    return train_df


def _get_next_fixture(summary: dict):
    """Returns the player's next unplayed fixture from their element-summary
    'fixtures' array (chronologically ordered, first entry = next match), or
    None if they have no fixture in the upcoming gameweek (a blank gameweek)
    OR if FPL simply hasn't published fixtures for the upcoming period yet.
    """
    fixtures = summary.get("fixtures", [])
    return fixtures[0] if fixtures else None


def next_gameweek(bootstrap: dict):
    """The gameweek currently being planned for."""
    for e in bootstrap.get("events", []):
        if e.get("is_next"):
            return e["id"]
    # Season over, or the flag isn't set yet — fall back to the first
    # unfinished gameweek.
    for e in bootstrap.get("events", []):
        if not e.get("finished"):
            return e["id"]
    return None


def _horizon_fixtures(summary: dict, first_gw, horizon: int) -> list:
    """The player's upcoming fixtures falling inside the planning horizon.

    Returns a list because a player can have two fixtures in one gameweek (a
    double) or none at all (a blank) — both are real, and both matter more
    than almost anything else the model says.
    """
    if first_gw is None:
        fixtures = summary.get("fixtures", [])
        return fixtures[:horizon]

    last_gw = first_gw + horizon - 1
    return [
        f for f in summary.get("fixtures", [])
        if f.get("event") is not None and first_gw <= f["event"] <= last_gw
    ]


def build_prediction_set(
    bootstrap: dict,
    df_with_rolling: pd.DataFrame,
    player_histories: dict,
    horizon: int = 1,
) -> pd.DataFrame:
    """Feature rows for the gameweeks we are planning for.

    Each row is one (player, upcoming fixture) pair: the player's MOST RECENT
    rolling form as the feature snapshot, combined with that specific
    fixture's opponent, venue and rest days. With horizon=1 this is one row
    per player for the next gameweek; with horizon=6 it spans the next six,
    which is what lets the optimizer see a fixture swing coming instead of
    buying into a wall.

    Emitting one row per fixture (rather than per player) is what makes
    double gameweeks work correctly — a player with two fixtures simply gets
    two rows, and their expected points add up the same way their real points
    would. Players with no fixture in a gameweek get no row for it, which is
    exactly right for a blank.

    If FPL hasn't published the upcoming fixture list at all (checked via
    FIXTURES_PUBLISHED_THRESHOLD across the whole player pool, not just one
    player), this falls back to one row per player carrying their last-known
    match context, instead of zeroing everyone out. That happens during the
    close season, when last season's history is still cached but the new
    fixture list isn't live yet.
    """
    latest = latest_form_snapshot(df_with_rolling)

    players_meta = {p["id"]: p for p in bootstrap["elements"]}
    team_strength = _team_strength_lookup(bootstrap)

    latest["selected_by_percent"] = latest["player_id"].map(
        lambda pid: float(players_meta.get(pid, {}).get("selected_by_percent", 0) or 0)
    )
    latest["now_cost"] = latest["player_id"].map(
        lambda pid: players_meta.get(pid, {}).get("now_cost", latest.loc[latest.player_id == pid, "now_cost"])
    )
    latest["status"] = latest["player_id"].map(lambda pid: players_meta.get(pid, {}).get("status", "a"))
    latest["chance_of_playing"] = latest["player_id"].map(
        lambda pid: players_meta.get(pid, {}).get("chance_of_playing_next_round")
    )
    latest["web_name"] = latest["player_id"].map(lambda pid: players_meta.get(pid, {}).get("web_name"))
    latest["team"] = latest["player_id"].map(lambda pid: players_meta.get(pid, {}).get("team"))
    latest["age"] = latest["player_id"].map(
        lambda pid: _player_age(players_meta.get(pid, {}).get("birth_date"))
    )

    first_gw = next_gameweek(bootstrap)

    # Which players have any upcoming fixture at all? This decides whether we
    # are looking at genuine blanks or at an unpublished fixture list.
    per_player_fixtures = {
        pid: _horizon_fixtures(player_histories.get(pid, {}), first_gw, horizon)
        for pid in latest["player_id"]
    }
    with_fixtures = sum(1 for f in per_player_fixtures.values() if f)
    fixtures_published = (
        with_fixtures / max(len(per_player_fixtures), 1)
    ) >= FIXTURES_PUBLISHED_THRESHOLD

    if not fixtures_published:
        logger.warning(
            "Fewer than %.0f%% of players have a published upcoming fixture — "
            "treating this as the close season (next fixture list not live yet), "
            "not a mass blank gameweek. Falling back to each player's last-known "
            "match context instead of zeroing predictions. Re-run once FPL "
            "publishes the new fixture list for a true forward-looking prediction.",
            FIXTURES_PUBLISHED_THRESHOLD * 100,
        )
        latest["has_fixture"] = [bool(per_player_fixtures[p]) for p in latest["player_id"]]
        latest["fixtures_published"] = False
        latest["gw"] = first_gw
        latest["fixture_index"] = 0
        return latest

    # --- One row per (player, upcoming fixture) inside the horizon ---
    rows = []
    for _, snapshot in latest.iterrows():
        pid = snapshot["player_id"]
        fixtures = per_player_fixtures.get(pid, [])
        previous_kickoff = snapshot.get("kickoff_time")

        if not fixtures:
            # A genuine blank across the whole horizon. Keep one row so the
            # player still appears in the output (predict_points zeroes it),
            # rather than vanishing from the pool entirely.
            row = snapshot.to_dict()
            row.update({"gw": first_gw, "fixture_index": 0, "has_fixture": False,
                        "fixtures_published": True})
            rows.append(row)
            continue

        for idx, fixture in enumerate(fixtures):
            is_home = bool(fixture.get("is_home"))
            opponent = fixture.get("team_a") if is_home else fixture.get("team_h")
            kickoff = _parse_kickoff(fixture.get("kickoff_time"))

            opp = team_strength.get(opponent, {})
            row = snapshot.to_dict()
            row.update({
                "gw": fixture.get("event", first_gw),
                "fixture_index": idx,
                "has_fixture": True,
                "fixtures_published": True,
                "was_home": int(is_home),
                "opponent_team": opponent,
                "opp_strength_attack": opp.get("attack", 1100),
                "opp_strength_defence": opp.get("defence", 1100),
                "fixture_difficulty": (
                    opp.get("defence", 1100) - snapshot["team_strength_attack"]
                ) / 100.0,
                # Rest measured against the previous match in this chain, so
                # a midweek-then-weekend double reads as congested rather than
                # every fixture being measured from the same past match.
                "days_since_last_match": (
                    (kickoff - previous_kickoff).days
                    if kickoff is not None and previous_kickoff is not None
                    and pd.notna(previous_kickoff)
                    else snapshot.get("days_since_last_match", 0)
                ),
            })
            rows.append(row)
            if kickoff is not None:
                previous_kickoff = kickoff

    out = pd.DataFrame(rows)
    logger.info(
        "Prediction set: %d rows over GW%s-%s (%d players)",
        len(out), first_gw, (first_gw or 0) + horizon - 1, len(latest),
    )
    return out