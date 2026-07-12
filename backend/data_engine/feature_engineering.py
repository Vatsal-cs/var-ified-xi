"""
File: feature_engineering.py
Path: fpl-optimizer/backend/data_engine/feature_engineering.py

Turns raw FPL API responses into a flat, per-player-per-gameweek DataFrame
with rolling-form features. Used both to build the XGBoost TRAINING set
(historical gameweeks -> actual points scored) and the PREDICTION set
(most recent form -> features for the upcoming gameweek).
"""

import logging
import pandas as pd
import numpy as np

from config import ROLLING_WINDOWS, MIN_MINUTES_HISTORY

logger = logging.getLogger(__name__)


def _team_strength_lookup(bootstrap: dict) -> dict:
    """Map team id -> dict of attack/defence strength ratings from bootstrap-static."""
    lookup = {}
    for t in bootstrap["teams"]:
        lookup[t["id"]] = {
            "attack": (t["strength_attack_home"] + t["strength_attack_away"]) / 2,
            "defence": (t["strength_defence_home"] + t["strength_defence_away"]) / 2,
        }
    return lookup


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
                "team_strength_attack": team_strength.get(meta.get("team"), {}).get("attack", 1100),
                "team_strength_defence": team_strength.get(meta.get("team"), {}).get("defence", 1100),
                "opp_strength_attack": team_strength.get(opp_id, {}).get("attack", 1100),
                "opp_strength_defence": team_strength.get(opp_id, {}).get("defence", 1100),
            })

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("No gameweek history rows built — check player_histories input.")
    df.sort_values(["player_id", "round"], inplace=True)
    return df


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Adds rolling-average form features per player, shifted by 1 gameweek
    so we never leak the current/target gameweek's own stats into training.
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

    # 'form' as FPL defines it loosely: average points over last 5 played gameweeks
    df["form"] = df["points_avg_5"]

    df["fixture_difficulty"] = (df["opp_strength_defence"] - df["team_strength_attack"]) / 100.0

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


def build_prediction_set(bootstrap: dict, df_with_rolling: pd.DataFrame) -> pd.DataFrame:
    """One row per currently-available player, using their MOST RECENT rolling
    form as the feature snapshot to predict next gameweek's points.
    """
    latest = (
        df_with_rolling.sort_values("round")
        .groupby("player_id", as_index=False)
        .tail(1)
        .copy()
    )

    players_meta = {p["id"]: p for p in bootstrap["elements"]}
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

    return latest
