"""
File: main.py
Path: fpl-optimizer/backend/main.py

THE SCRIPT YOU RUN LOCALLY.

Usage:
    cd fpl-optimizer/backend
    python -m venv venv && source venv/bin/activate   # (or venv\\Scripts\\activate on Windows)
    pip install -r requirements.txt
    python main.py

Pipeline:
    1. Fetch bootstrap-static + fixtures + per-player histories from the free FPL API
    2. Build a rolling-form feature table
    3. Train (or reload) an XGBoost model and predict next-gameweek points for every player
    4. Solve the PuLP MILP optimizer for the best 15-man squad / starting XI / captain
    5. Write optimized_team.json to backend/data/output/ AND frontend/public/
"""

import sys
import json
import logging
from datetime import datetime, timezone

import config
from data_engine import fetch_data, feature_engineering, train_model, optimizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def build_output_json(bootstrap: dict, predictions_df, result: dict) -> dict:
    """Assembles the final clean JSON contract the frontend will consume."""
    teams_lookup = {t["id"]: t["name"] for t in bootstrap["teams"]}
    pos_lookup = config.POSITIONS
    pred_lookup = predictions_df.set_index("player_id").to_dict(orient="index")

    def player_payload(pid: int, is_captain: bool = False, is_vice: bool = False) -> dict:
        row = pred_lookup[pid]
        return {
            "player_id": int(pid),
            "name": row.get("web_name"),
            "position": pos_lookup.get(row.get("element_type")),
            "team": teams_lookup.get(row.get("team"), "Unknown"),
            "now_cost_m": round(float(row.get("now_cost", 0)) / 10, 1),
            "predicted_points": float(row.get("predicted_points", 0)),
            "is_captain": is_captain,
            "is_vice_captain": is_vice,
        }

    starting_xi = [
        player_payload(pid, is_captain=(pid == result["captain_id"]),
                        is_vice=(pid == result["vice_captain_id"]))
        for pid in result["starting_ids"]
    ]
    bench = [player_payload(pid) for pid in result["bench_ids"]]

    current_gw = next(
        (e["id"] for e in bootstrap["events"] if e.get("is_next")),
        None,
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gameweek": current_gw,
        "budget_used_m": round(result["total_cost"] / 10, 1),
        "budget_total_m": round(config.BUDGET / 10, 1),
        "predicted_total_points": result["total_predicted_points"],
        "starting_xi": starting_xi,
        "bench": bench,
        "captain_id": result["captain_id"],
        "vice_captain_id": result["vice_captain_id"],
    }


def run_pipeline() -> None:
    logger.info("=== FPL Optimizer: local pipeline starting ===")

    # 1. Fetch raw data
    bootstrap = fetch_data.fetch_bootstrap_static()
    fetch_data.fetch_fixtures()  # cached for future FDR-based feature work
    player_ids = [p["id"] for p in bootstrap["elements"]]
    histories = fetch_data.fetch_all_player_histories(player_ids)

    # 2. Feature engineering
    logger.info("Building feature table...")
    history_df = feature_engineering.build_gameweek_history_df(bootstrap, histories)
    history_df = feature_engineering.add_rolling_features(history_df)

    train_df = feature_engineering.build_training_set(history_df)
    predict_df = feature_engineering.build_prediction_set(bootstrap, history_df)

    if train_df.empty or len(train_df) < 50:
        logger.error(
            "Not enough historical gameweek data yet to train (only %d rows). "
            "Early season — try again after a few more gameweeks, or lower "
            "MIN_MINUTES_HISTORY in config.py.", len(train_df)
        )
        sys.exit(1)

    # 3. Train / predict
    logger.info("Training XGBoost model on %d historical rows...", len(train_df))
    model = train_model.train_xgb_model(train_df)
    predictions_df = train_model.predict_points(model, predict_df)

    # 4. Optimize
    logger.info("Solving MILP squad optimizer over %d available players...", len(predictions_df))
    result = optimizer.optimize_squad(predictions_df)

    # 5. Write output
    output = build_output_json(bootstrap, predictions_df, result)

    config.OUTPUT_JSON_PATH.write_text(json.dumps(output, indent=2))
    config.FRONTEND_JSON_PATH.write_text(json.dumps(output, indent=2))

    logger.info("Wrote %s", config.OUTPUT_JSON_PATH)
    logger.info("Wrote %s", config.FRONTEND_JSON_PATH)
    logger.info(
        "Squad: %.1fm / %.1fm | Predicted GW points: %.2f",
        output["budget_used_m"], output["budget_total_m"], output["predicted_total_points"],
    )
    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    run_pipeline()
