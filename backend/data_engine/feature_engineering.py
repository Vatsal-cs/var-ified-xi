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

from config import ROLLING_WINDOWS, FALLBACK_AGE

logger = logging.getLogger(__name__)

# If fewer than this fraction of players have any upcoming fixture at all,
# treat it as "fixtures not published yet" rather than "genuine blanks".
# A real blank gameweek (e.g. FA Cup replay clashes) affects at most a
# couple of clubs — nowhere near half the league.
FIXTURES_PUBLISHED_THRESHOLD = 0.5


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


def build_gameweek_history_df(bootstrap: dict, player_histories: dict) -> pd.DataFrame:
    """Flattens every player's gameweek-by-gameweek 'history' entries into one
    long DataFrame: one row = one player's performance in one past gameweek.
    """
    team_strength = _team_strength_lookup(bootstrap)
    players_meta = {p["id"]: p for p in bootstrap["elements"]}

    rows = []
    for pid, summary in player_histories.items():
        meta = players_meta.get(pid)
        if meta is None:
            continue
        for gw in summary.get("history", []):
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
            })

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

    for w in ROLLING_WINDOWS:
        df[f"minutes_avg_{w}"] = grp["minutes"].apply(
            lambda s: s.shift(1).rolling(w, min_periods=1).mean()
        )
        df[f"points_avg_{w}"] = grp["total_points"].apply(
            lambda s: s.shift(1).rolling(w, min_periods=1).mean()
        )
        df[f"ict_index_avg_{w}"] = grp["ict_index"].apply(
            lambda s: s.shift(1).rolling(w, min_periods=1).mean()
        )

    df["influence_avg_3"] = grp["influence"].apply(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    df["creativity_avg_3"] = grp["creativity"].apply(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    df["threat_avg_3"] = grp["threat"].apply(lambda s: s.shift(1).rolling(3, min_periods=1).mean())

    # xG/xA-derived rolling features — a stronger forward-looking signal
    # than ICT index alone, since ICT is partly backward-looking descriptive
    # scoring rather than a true underlying-chance-quality metric.
    if "expected_goal_involvements" in df.columns:
        df["xgi_avg_3"] = grp["expected_goal_involvements"].apply(
            lambda s: s.shift(1).rolling(3, min_periods=1).mean()
        )
    else:
        df["xgi_avg_3"] = 0.0
    if "expected_goals_conceded" in df.columns:
        df["xgc_avg_3"] = grp["expected_goals_conceded"].apply(
            lambda s: s.shift(1).rolling(3, min_periods=1).mean()
        )
    else:
        df["xgc_avg_3"] = 0.0

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


def build_training_set(df_with_rolling: pd.DataFrame) -> pd.DataFrame:
    """Historical rows used to TRAIN the model: every past gameweek row
    (minus the very first appearance per player, which has no rolling history).
    """
    train_df = df_with_rolling[df_with_rolling["minutes_avg_3"] > 0].copy()
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


def build_prediction_set(bootstrap: dict, df_with_rolling: pd.DataFrame, player_histories: dict) -> pd.DataFrame:
    """One row per currently-available player, using their MOST RECENT rolling
    form as the feature snapshot, but their NEXT UPCOMING fixture's opponent
    and venue — not their last-played match's opponent — WHEN that data is
    actually available.

    If FPL hasn't published the upcoming fixture list at all (checked via
    FIXTURES_PUBLISHED_THRESHOLD across the whole player pool, not just one
    player), this falls back to each player's last-known match context
    instead of zeroing everyone out. This commonly happens during the close
    season, when last season's history is still cached but next season's
    fixtures haven't gone live yet.
    """
    latest = (
        df_with_rolling.sort_values("round")
        .groupby("player_id", as_index=False)
        .tail(1)
        .copy()
    )

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

    # Preserve the LAST-PLAYED-match context (already computed by
    # add_rolling_features) before we potentially overwrite it below —
    # this is the fallback data source if fixtures aren't published yet.
    last_opp_attack = latest["opp_strength_attack"].copy()
    last_opp_defence = latest["opp_strength_defence"].copy()
    last_was_home = latest["was_home"].copy()
    last_fixture_difficulty = latest["fixture_difficulty"].copy()

    # --- Pull each player's NEXT fixture, not their last one ---
    has_fixture, next_was_home, opp_ids, next_kickoffs = [], [], [], []
    for pid in latest["player_id"]:
        summary = player_histories.get(pid, {})
        nxt = _get_next_fixture(summary)
        if nxt is None:
            has_fixture.append(False)
            next_was_home.append(0)
            opp_ids.append(None)
            next_kickoffs.append(None)
            continue

        is_home = bool(nxt.get("is_home"))
        opponent = nxt.get("team_a") if is_home else nxt.get("team_h")
        has_fixture.append(True)
        next_was_home.append(int(is_home))
        opp_ids.append(opponent)
        next_kickoffs.append(_parse_kickoff(nxt.get("kickoff_time")))

    latest["has_fixture"] = has_fixture

    # Decide: are fixtures actually published league-wide, or are we in the
    # close-season gap where nobody has one yet?
    fixtures_published = (sum(has_fixture) / max(len(has_fixture), 1)) >= FIXTURES_PUBLISHED_THRESHOLD
    latest["fixtures_published"] = fixtures_published

    if not fixtures_published:
        logger.warning(
            "Fewer than %.0f%% of players have a published upcoming fixture — "
            "treating this as the close season (next fixture list not live yet), "
            "not a mass blank gameweek. Falling back to each player's last-known "
            "match context instead of zeroing predictions. Re-run once FPL "
            "publishes the new fixture list for a true forward-looking prediction.",
            FIXTURES_PUBLISHED_THRESHOLD * 100,
        )

    next_opp_attack, next_opp_defence, next_fixture_difficulty, final_was_home = [], [], [], []
    for i, (has_fix, opp) in enumerate(zip(has_fixture, opp_ids)):
        if has_fix:
            next_opp_attack.append(team_strength.get(opp, {}).get("attack", 1100))
            next_opp_defence.append(team_strength.get(opp, {}).get("defence", 1100))
            final_was_home.append(next_was_home[i])
        elif not fixtures_published:
            # Close-season fallback: reuse last-played-match context rather
            # than a neutral default or a hard zero.
            next_opp_attack.append(last_opp_attack.iloc[i])
            next_opp_defence.append(last_opp_defence.iloc[i])
            final_was_home.append(last_was_home.iloc[i])
        else:
            # Genuine isolated blank gameweek — neutral placeholder, doesn't
            # matter since predict_points will zero this player's points.
            next_opp_attack.append(1100)
            next_opp_defence.append(1100)
            final_was_home.append(0)

    latest["opp_strength_attack"] = next_opp_attack
    latest["opp_strength_defence"] = next_opp_defence
    latest["was_home"] = final_was_home

    if fixtures_published:
        latest["fixture_difficulty"] = (
            latest["opp_strength_defence"] - latest["team_strength_attack"]
        ) / 100.0
    else:
        latest["fixture_difficulty"] = last_fixture_difficulty

    # Rest days going into the upcoming match, where known; otherwise fall
    # back to the last-known gap between matches.
    last_kickoffs = latest["kickoff_time"] if "kickoff_time" in latest.columns else [None] * len(latest)
    rest_days = []
    for i, (last_ko, next_ko) in enumerate(zip(last_kickoffs, next_kickoffs)):
        if last_ko is not None and next_ko is not None and pd.notna(last_ko):
            rest_days.append((next_ko - last_ko).days)
        else:
            rest_days.append(latest["days_since_last_match"].iloc[i] if "days_since_last_match" in latest.columns else 0)
    latest["days_since_last_match"] = rest_days

    return latest