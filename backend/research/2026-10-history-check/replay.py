"""This season (2026-27) replayed GW2-6 with different training data.

    python research/2026-10-history-check/replay.py <variant> <seed>

Variants: production (2023-24, 2024-25, 2025-26 + this season, as live),
last_season (2025-26 + this season), this_season (this season only),
recency (production's data, older seasons down-weighted 0.7 a season).
Walk-forward: each gameweek is predicted from what was known before it.
"""
import json, logging, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
logging.basicConfig(level=logging.ERROR)
variant, seed = sys.argv[1], int(sys.argv[2])
sys.argv = ["x"]
import config
import data_engine.fetch_data as fd
import main as M
from data_engine import backtest, feature_engineering as fe, fetch_data, historical_data
fd._cache_path = lambda name: config.RAW_DIR / f"{name}_2026-10-15.json"     # GW1-6 complete, GW7 not started
boot = fetch_data.fetch_bootstrap_static(); fixtures = fetch_data.fetch_fixtures()
hists = fetch_data.fetch_all_player_histories([p["id"] for p in boot["elements"]])
config.MODEL_BAG_SIZE = 1
config.MODEL_SEED = seed
seasons = {"production": ["2023-24", "2024-25", "2025-26"], "recency": ["2023-24", "2024-25", "2025-26"],
           "last_season": ["2025-26"], "this_season": []}[variant]
past = None
if seasons:
    config.HISTORICAL_SEASONS = seasons
    past = fe.build_training_set(fe.add_rolling_features(historical_data.build_historical_training_df()))
cur = fe.build_gameweek_history_df(boot, hists, fixtures=fixtures)
cur = fe.add_rolling_features(cur)
if config.OTHER_MATCHES:
    M._attach_other_matches(cur, boot)
cur = cur[cur["round"] <= 6]
v = backtest.VARIANTS["recency" if variant == "recency" else "production"]
s = backtest.simulate_season(cur, v, prior_seasons_df=past, start_gw=2)
out = {"variant": variant, "seed": seed, "points": s["total_points"], "mae": s["mae"], "spearman": s["spearman"],
       "by_gw": s.get("by_gw") or s.get("gameweeks")}
here = os.path.dirname(os.path.abspath(__file__))
json.dump(out, open(os.path.join(here, f"r_{variant}_s{seed}.json"), "w"), default=str)
print(variant, seed, s["total_points"], round(s["mae"], 3), round(s["spearman"], 3))
