"""Descriptive: 2026-27 GW2-5 replay, team form vs the last-season-ratings fallback."""
import logging, sys
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
logging.basicConfig(level=logging.ERROR); sys.argv = ["x"]
import numpy as np
import config
import data_engine.fetch_data as fd
from data_engine import backtest, feature_engineering, fetch_data, historical_data
fd._cache_path = lambda name: config.RAW_DIR / f"{name}_2026-10-09.json"     # GW1-5 complete
boot = fetch_data.fetch_bootstrap_static(); fixtures = fetch_data.fetch_fixtures()
hists = fetch_data.fetch_all_player_histories([p["id"] for p in boot["elements"]])
config.MODEL_BAG_SIZE = 1
base_features = list(config.FEATURE_COLUMNS)
res = {}
for tf in (False, True):
    config.TEAM_FORM = tf
    config.FEATURE_COLUMNS = config.team_form_features(base_features) if tf else list(base_features)
    past = feature_engineering.build_training_set(feature_engineering.add_rolling_features(historical_data.build_historical_training_df()))
    cur = feature_engineering.add_rolling_features(feature_engineering.build_gameweek_history_df(boot, hists, fixtures=fixtures))
    cur = cur[cur["round"] <= 5]
    for seed in (42, 7, 13):
        config.MODEL_SEED = seed
        s = backtest.simulate_season(cur, backtest.VARIANTS["production"], prior_seasons_df=past, start_gw=2)
        res.setdefault(tf, []).append((s["total_points"], s["mae"], s["spearman"], s["brier60"] or float("nan")))
for tf, rows in res.items():
    pts, mae, rr, br = np.mean(rows, axis=0)
    print(f"{'team form (xG)' if tf else 'last-season FPL ratings (live now)':<36} GW2-5 squad points {pts:6.1f}  "
          f"MAE {mae:.3f}  rank-r {rr:.3f}   per seed {[r[0] for r in rows]}")
