"""Walk-forward replay of the shipping model that keeps every projection.

backtest.py only keeps the squad it picked; the bias tests need each
player-gameweek's projection next to what happened. One process per season:

    python research/2026-10-projection-bias/collect.py 2024-25
    python research/2026-10-projection-bias/collect.py 2025-26 --prior 2024-25
    python research/2026-10-projection-bias/collect.py live       # 2026-27 GW2-6

Writes rows_<season>.csv next to this file.
"""
import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np
import pandas as pd

import config
from data_engine import backtest, feature_engineering, fetch_data, historical_data, train_model

HERE = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger("collect")

KEEP = ["player_id", "web_name", "team", "element_type", "now_cost", "round", "kickoff_time",
        "status", "chance_of_playing", "dc_avg_5", "xgi_avg_3", "points_avg_5",
        "minutes_avg_3", "starts_avg_3"]


def _recent(season_df: pd.DataFrame) -> pd.DataFrame:
    """Per (player, round): minutes of the previous three matches and points of
    the previous five, all from rounds strictly before it — what was known at
    that round's deadline."""
    per = (season_df.groupby(["player_id", "round"], as_index=False)
           .agg(minutes=("minutes", "sum"), points=(config.TARGET_COL, "sum"))
           .sort_values(["player_id", "round"]))
    g = per.groupby("player_id")
    for k in (1, 2, 3):
        per[f"prev_min_{k}"] = g["minutes"].shift(k)
    for k in range(1, 6):
        per[f"prev_pts_{k}"] = g["points"].shift(k)
        per[f"prev_played_{k}"] = g["minutes"].shift(k).gt(0)
    return per.drop(columns=["minutes", "points"])


def walk(season_df: pd.DataFrame, prior: pd.DataFrame, rounds) -> pd.DataFrame:
    out = []
    for gw in rounds:
        started = time.time()
        train = feature_engineering.build_training_set(season_df[season_df["round"] < gw])
        if prior is not None:
            train = pd.concat([train, prior], ignore_index=True)
        model = train_model.train_models(train, save=False)

        fixtures = backtest.frozen_form_for_doubles(season_df[season_df["round"] == gw])
        pred = train_model.predict_points(model, fixtures)
        X = train_model._prep_X(fixtures)
        rows = fixtures[[c for c in KEEP if c in fixtures.columns]].copy()
        rows["pred"] = pred["predicted_points"].to_numpy()
        rows["p60"] = backtest._p60(model, fixtures)["p"].to_numpy()
        rows["pts_if_60"] = train_model._bag_mean(
            model, lambda m: train_model._predict_conditional_points(m, X, fixtures["element_type"]))
        rows["actual"] = fixtures[config.TARGET_COL].to_numpy()
        rows["minutes"] = fixtures["minutes"].to_numpy()
        out.append(rows)
        logger.info("GW%-2d %d rows, %.0fs", gw, len(rows), time.time() - started)
    return pd.concat(out, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("season")
    ap.add_argument("--prior", nargs="*", default=[])
    ap.add_argument("--last-gw", type=int, default=6, help="live season only")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    for name in ("data_engine.train_model", "data_engine.feature_engineering",
                 "data_engine.historical_data", "data_engine.fetch_data"):
        logging.getLogger(name).setLevel(logging.WARNING)
    config.MODEL_SEED = 42

    if args.season == "live":
        boot = fetch_data.fetch_bootstrap_static()
        fixtures = fetch_data.fetch_fixtures()
        hists = fetch_data.fetch_all_player_histories([p["id"] for p in boot["elements"]])
        season_df = feature_engineering.add_rolling_features(
            feature_engineering.build_gameweek_history_df(boot, hists, fixtures=fixtures))
        season_df = season_df[season_df["round"] <= args.last_gw]
        prior = feature_engineering.build_training_set(
            feature_engineering.add_rolling_features(historical_data.build_historical_training_df()))
        rounds = range(2, args.last_gw + 1)
    else:
        seasons = args.prior + [args.season]
        frames = {s: backtest.load_season_frame(s, i) for i, s in enumerate(seasons)}
        season_df = frames[args.season]
        prior = None
        if args.prior:
            prior = pd.concat([feature_engineering.build_training_set(frames[s]) for s in args.prior],
                              ignore_index=True)
        rounds = sorted(r for r in season_df["round"].unique() if r >= 2)

    rows = walk(season_df, prior, rounds)
    rows = rows.merge(_recent(season_df), on=["player_id", "round"], how="left")
    path = os.path.join(HERE, f"rows_{args.season}.csv")
    rows.to_csv(path, index=False)
    logger.info("wrote %d rows to %s", len(rows), path)


if __name__ == "__main__":
    main()
