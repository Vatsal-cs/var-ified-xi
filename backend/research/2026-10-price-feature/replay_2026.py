"""Descriptive: 2026-27 GW2-6 replay, with and without price (and ownership)
as model inputs. Too small and too seen to decide anything.

    python research/2026-10-price-feature/replay_2026.py
"""
import logging, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
logging.basicConfig(level=logging.ERROR)
import numpy as np
import config
from data_engine import backtest, feature_engineering, fetch_data, historical_data

boot = fetch_data.fetch_bootstrap_static()
fixtures = fetch_data.fetch_fixtures()
hists = fetch_data.fetch_all_player_histories([p["id"] for p in boot["elements"]])
config.MODEL_BAG_SIZE = 1
LAST_GW = 6

past = feature_engineering.build_training_set(
    feature_engineering.add_rolling_features(historical_data.build_historical_training_df()))
cur = feature_engineering.add_rolling_features(
    feature_engineering.build_gameweek_history_df(boot, hists, fixtures=fixtures))
cur = cur[cur["round"] <= LAST_GW]

res = {}
for name in ("production", "no_price", "no_price_own"):
    v = backtest.VARIANTS[name]
    with (v.context() if v.context else backtest.contextlib.nullcontext()):
        for seed in (42, 7, 13):
            config.MODEL_SEED = seed
            s = backtest.simulate_season(cur, v, prior_seasons_df=past, start_gw=2)
            res.setdefault(name, []).append((s["total_points"], s["mae"], s["spearman"]))
for name, rows in res.items():
    pts, mae, rr = np.mean(rows, axis=0)
    print(f"{name:<14} GW2-{LAST_GW} squad points {pts:6.1f}  MAE {mae:.3f}  rank-r {rr:.3f}  "
          f"per seed {[r[0] for r in rows]}")
