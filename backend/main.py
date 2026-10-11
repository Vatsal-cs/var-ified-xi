"""
File: main.py
Path: var-ified-xi/backend/main.py

VAR-ified XI — local data engine entrypoint.

THE SCRIPT YOU RUN LOCALLY.

Usage:
    cd var-ified-xi/backend
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
import argparse
import json
import logging
import os
import pandas as pd
from datetime import datetime, timezone

import config
from data_engine import (
    chips,
    rivals,
    entry_data,
    fetch_data,
    feature_engineering,
    historical_data,
    injury_log,
    optimizer,
    planner,
    train_model,
    transfer_optimizer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def order_bench(bench_ids: list, pred_lookup: dict) -> list:
    """Orders the bench the way FPL uses it for automatic substitutions.

    The reserve keeper sits in his own slot and can only ever replace the
    keeper, so he comes first. The outfield three are ranked by what they are
    actually worth as substitutes: expected points weighted by how likely the
    player is to have played at all. A high-scoring player who is doubtful is
    a worse first sub than a certain starter who scores a little less.
    """
    def autosub_value(pid):
        row = pred_lookup.get(pid, {})
        return float(row.get("predicted_points", 0)) * float(row.get("p_full", 1.0))

    keepers = [p for p in bench_ids if pred_lookup.get(p, {}).get("element_type") == 1]
    outfield = [p for p in bench_ids if p not in keepers]
    return keepers + sorted(outfield, key=autosub_value, reverse=True)


def build_output_json(bootstrap: dict, predictions_df, result: dict,
                      plan: dict = None, team_state=None,
                      chip_advice: list = None, chip_watch: dict = None,
                      league_view: dict = None, chip_expiry: dict = None,
                      captain_override: dict = None, wildcard_option: dict = None) -> dict:
    """Assembles the final clean JSON contract the frontend will consume."""
    teams_lookup = {t["id"]: t["name"] for t in bootstrap["teams"]}
    pos_lookup = config.POSITIONS
    pred_lookup = predictions_df.set_index("player_id").to_dict(orient="index")

    def player_payload(pid: int, is_captain: bool = False, is_vice: bool = False) -> dict:
        row = pred_lookup.get(pid, {})
        return {
            "player_id": int(pid),
            "name": row.get("web_name"),
            "position": pos_lookup.get(row.get("element_type")),
            "team": teams_lookup.get(row.get("team"), "Unknown"),
            "now_cost_m": round(float(row.get("now_cost", 0)) / 10, 1),
            "predicted_points": float(row.get("predicted_points", 0)),
            "horizon_points": float(row.get("horizon_points", 0)),
            # {gameweek: expected points} across the planning horizon — this is
            # what lets the dashboard show a fixture run rather than a number.
            "xp_by_gw": {str(k): v for k, v in (row.get("xp_by_gw") or {}).items()},
            "start_probability": round(float(row.get("p_full", 1.0)), 2),
            "is_captain": is_captain,
            "is_vice_captain": is_vice,
        }

    starting_xi = [
        player_payload(pid, is_captain=(pid == result["captain_id"]),
                        is_vice=(pid == result["vice_captain_id"]))
        for pid in result["starting_ids"]
    ]
    bench = [player_payload(pid) for pid in order_bench(result["bench_ids"], pred_lookup)]

    current_gw = feature_engineering.next_gameweek(bootstrap)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gameweek": current_gw,
        "horizon_gws": config.HORIZON_GWS,
        "mode": "transfer_plan" if plan else "fresh_squad",
        "budget_used_m": round(result["total_cost"] / 10, 1),
        "budget_total_m": round(config.BUDGET / 10, 1),
        "predicted_total_points": result["total_predicted_points"],
        "starting_xi": starting_xi,
        "bench": bench,
        "captain_id": result["captain_id"],
        "vice_captain_id": result["vice_captain_id"],
    }

    if chip_advice:
        output["chip_advice"] = chip_advice
    if chip_watch:
        output["chip_watch"] = chip_watch
    if league_view:
        output["league"] = league_view
    if chip_expiry:
        output["chip_expiry"] = chip_expiry
    if captain_override:
        output["captain_override"] = captain_override
    if wildcard_option:
        output["wildcard_option"] = wildcard_option
    if plan:
        output["transfer_plan"] = _plan_payload(plan, pred_lookup, pos_lookup, teams_lookup)
    if team_state:
        output["team"] = {
            "name": team_state.name,
            "entry_id": team_state.entry_id,
            "bank_m": round(team_state.bank / 10, 1),
            "squad_value_m": round(team_state.squad_value / 10, 1),
            "free_transfers": team_state.free_transfers,
            "chips_available": team_state.chips_available,
        }

    return output


def _plan_payload(plan: dict, pred_lookup: dict, pos_lookup: dict, teams_lookup: dict) -> dict:
    """The multi-gameweek plan, trimmed to what the dashboard shows."""
    def decorate(entry):
        row = pred_lookup.get(entry["player_id"], {})
        return {
            **entry,
            "position": pos_lookup.get(row.get("element_type")),
            "team": teams_lookup.get(row.get("team"), "Unknown"),
        }

    weeks = []
    for week in plan["weeks"]:
        weeks.append({
            "gameweek": week["gameweek"],
            "transfers_in": [decorate(p) for p in week["transfers_in"]],
            "transfers_out": [decorate(p) for p in week["transfers_out"]],
            "transfer_count": week["transfer_count"],
            "free_transfers": week["free_transfers"],
            "hits": week["hits"],
            "hit_cost": week["hit_cost"],
            "bank_m": week["bank_m"],
            "predicted_points": week["predicted_points"],
            "captain_id": week["captain_id"],
        })

    payload = {"weeks": weeks}

    rec = plan.get("hit_recommendation")
    if rec:
        payload["hit_recommendation"] = {
            **rec,
            "extra_transfers_in": [decorate(p) for p in rec["extra_transfers_in"]],
            "extra_transfers_out": [decorate(p) for p in rec["extra_transfers_out"]],
        }
    return payload


def run_pipeline(team_id: int = None) -> None:
    logger.info("=== VAR-ified XI: local data engine starting ===")

    # 1. Fetch raw data
    bootstrap = fetch_data.fetch_bootstrap_static()
    fixtures = fetch_data.fetch_fixtures()
    player_ids = [p["id"] for p in bootstrap["elements"]]
    histories = fetch_data.fetch_all_player_histories(player_ids)

    # Log today's availability flags (injured/doubtful/suspended players)
    # so repeat fitness concerns are visible even after the API's own
    # "chance of playing" resets to 100% between flare-ups.
    injury_log.update_injury_log(bootstrap)
    flag_counts = injury_log.get_flag_counts()

    # 2. Feature engineering
    logger.info("Building feature table...")
    history_df = feature_engineering.build_gameweek_history_df(bootstrap, histories, fixtures=fixtures)
    history_df = feature_engineering.add_rolling_features(history_df)

    train_df = feature_engineering.build_training_set(history_df)
    predict_df = feature_engineering.build_prediction_set(
        bootstrap, history_df, histories, horizon=config.HORIZON_GWS
    )

    # 3. Historical multi-season augmentation (training only, never prediction)
    logger.info("Fetching historical seasons for training augmentation...")
    historical_raw = historical_data.build_historical_training_df()
    historical_train_df = pd.DataFrame()
    if not historical_raw.empty:
        historical_with_rolling = feature_engineering.add_rolling_features(historical_raw)
        historical_train_df = feature_engineering.build_training_set(historical_with_rolling)
        logger.info("Historical augmentation: %d additional training rows", len(historical_train_df))

    # The model trains on the current season AND past ones, so sufficiency has
    # to be judged on the total. Checking the current season alone would abort
    # every run in August — exactly the weeks where good picks compound most.
    total_training_rows = len(train_df) + len(historical_train_df)
    if total_training_rows < 500:
        logger.error(
            "Not enough gameweek data to train: %d current-season rows + %d "
            "historical rows. Check that the historical seasons in "
            "config.HISTORICAL_SEASONS are reachable.",
            len(train_df), len(historical_train_df),
        )
        sys.exit(1)

    if len(train_df) < 50:
        logger.warning(
            "Only %d current-season training rows so far — predictions lean "
            "almost entirely on past seasons and on each player's price and "
            "fixture. Expect them to sharpen as gameweeks accumulate.",
            len(train_df),
        )

    # 4. Train / predict
    logger.info("Training 2-stage model (minutes classifier + conditional points) on %d current-season rows...", len(train_df))
    model_bundle = train_model.train_models(train_df, historical_df=historical_train_df)

    # One prediction per (player, upcoming fixture), then folded back to one
    # row per player carrying both next-gameweek and whole-horizon expectations.
    fixture_predictions = train_model.predict_points(model_bundle, predict_df, flag_counts)
    predictions_df = feature_engineering.aggregate_horizon(fixture_predictions)

    # 5. Optimize — either a fresh squad, or transfers from the team you own
    upcoming_gw = feature_engineering.next_gameweek(bootstrap)
    plan, team_state, captain_override = None, None, None

    if team_id:
        team_state = entry_data.build_team_state(
            team_id, bootstrap, histories, upcoming_gw
        )
        result, plan = _plan_from_team(predictions_df, team_state, upcoming_gw)
        captain_override = _apply_armband_override(result, plan, predictions_df, upcoming_gw)
    else:
        logger.info("Solving MILP squad optimizer over %d available players (horizon: %d GWs)...",
                    len(predictions_df), config.HORIZON_GWS)
        result = optimizer.optimize_squad(predictions_df, objective_col="horizon_points")

    # 6. Chip advice from the fixture calendar. Actionable advice only covers
    # the planning horizon (it needs to know your actual squad that week);
    # the full-season scan is a lightweight "is there even anything to
    # watch for" check so the dashboard can say so explicitly instead of
    # going quiet, which reads the same as broken.
    chip_advice = chips.advise(
        fixtures, bootstrap["teams"], upcoming_gw,
        chips_available=team_state.chips_available if team_state else None,
        predictions_df=predictions_df,
        owned_squad=result["squad_ids"] if team_state else None,
        bench_ids=result["bench_ids"],
    )
    season_scan = chips.scan_full_season(fixtures, bootstrap["teams"], last_finished_gw=upcoming_gw - 1)
    chip_watch = {
        "checked_through_gw": 38,
        "next_double_gw": min((d["gameweek"] for d in season_scan["doubles"]), default=None),
        "next_blank_gw": min((b["gameweek"] for b in season_scan["blanks"]), default=None),
    }
    # Chips come in half-season sets and an unplayed one is lost at its
    # window's deadline, so the dashboard needs to say when — and what the
    # best week in sight is worth — not just wait for a double gameweek.
    chip_expiry = None
    if team_state:
        chip_expiry = chips.expiry_plan(team_state.chip_deadlines, upcoming_gw,
                                        plan, predictions_df)

    # 6b. What the people you're actually playing against own. Decision
    # support only — see rivals.py on why this deliberately doesn't feed the
    # optimizer. Never fatal: a league that can't be read just isn't shown.
    league_view = None
    if team_id:
        league_view = rivals.build_league_view(team_id, bootstrap, upcoming_gw)

    # 6c. Is the Wildcard worth playing this week? Computed every refresh
    # while it's in hand, so the answer is on the dashboard without anyone
    # having to run anything.
    wildcard_option = None
    if team_state and "wildcard" in (team_state.chips_available or []):
        try:
            wildcard_option = _wildcard_option(predictions_df, team_state, upcoming_gw,
                                               plan, league_view,
                                               {t["id"]: t["name"] for t in bootstrap["teams"]})
        except Exception as e:                      # never fatal to the refresh
            logger.warning("Wildcard check skipped: %s", e)

    # 7. Write output
    output = build_output_json(bootstrap, predictions_df, result, plan=plan,
                               team_state=team_state, chip_advice=chip_advice,
                               league_view=league_view,
                               chip_expiry=chip_expiry,
                               chip_watch=chip_watch,
                               captain_override=captain_override,
                               wildcard_option=wildcard_option)

    config.OUTPUT_JSON_PATH.write_text(json.dumps(output, indent=2))
    config.FRONTEND_JSON_PATH.write_text(json.dumps(output, indent=2))

    logger.info("Wrote %s", config.OUTPUT_JSON_PATH)
    logger.info("Wrote %s", config.FRONTEND_JSON_PATH)
    _log_summary(output)
    logger.info("=== VAR-ified XI: decision confirmed, no VAR check needed ===")


def _apply_armband_override(result: dict, plan: dict, predictions_df, gameweek) -> dict | None:
    """Your own captain and vice for this gameweek (config.OVERRIDES_PATH),
    in place of the model's. Applied on every refresh so the scheduled runs
    don't undo it, and ignored once that gameweek has passed or if either
    player isn't in this week's XI any more — then the model's pick stands
    and the log says why. Returns the model's own pick, for the dashboard to
    show alongside yours, or None when nothing was overridden.
    """
    path = config.OVERRIDES_PATH
    if not path.exists():
        return None
    try:
        wanted = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Ignoring %s: %s", path.name, e)
        return None
    if wanted.get("gameweek") != gameweek:
        return None

    cap, vice = wanted.get("captain_id"), wanted.get("vice_captain_id")
    xi = set(result["starting_ids"])
    if cap not in xi or (vice is not None and vice not in xi) or cap == vice:
        logger.warning("Armband override for GW%s ignored: %s/%s aren't both in this "
                       "week's XI. Using the model's pick.", gameweek,
                       wanted.get("captain"), wanted.get("vice_captain"))
        return None

    model_pick = {"model_captain_id": result["captain_id"],
                  "model_vice_captain_id": result["vice_captain_id"]}
    if cap != result["captain_id"]:
        # The armband's second copy of points moves with it.
        proj = predictions_df.set_index("player_id")["predicted_points"].to_dict()
        result["total_predicted_points"] = round(
            result["total_predicted_points"] - proj.get(result["captain_id"], 0) + proj.get(cap, 0), 2)
    result["captain_id"], result["vice_captain_id"] = cap, vice
    if plan and plan.get("weeks"):
        plan["weeks"][0]["captain_id"] = cap
    logger.info("Armband: your pick %s (C) / %s (VC) for GW%s; the model had "
                "different ones.", wanted.get("captain"), wanted.get("vice_captain"), gameweek)
    return model_pick


def _wildcard_option(predictions_df, team_state, upcoming_gw, free_plan: dict,
                     league_view: dict = None, team_names: dict = None) -> dict:
    """The same six-week plan with a Wildcard played this gameweek, against
    the free-transfer plan the dashboard already recommends."""
    xp_by_gw = {
        int(row["player_id"]): {int(k): float(v) for k, v in (row["xp_by_gw"] or {}).items()}
        for _, row in predictions_df.iterrows()
    }
    gameweeks = [upcoming_gw + i for i in range(config.HORIZON_GWS)]
    logger.info("Checking a Wildcard this gameweek...")
    wild = transfer_optimizer.plan_transfers(predictions_df, team_state, xp_by_gw, gameweeks,
                                             max_total_hits=0, wildcard=True)
    week = wild["weeks"][0]
    p = predictions_df.set_index("player_id")
    proj = p["predicted_points"].to_dict()
    captain, vice = planner.pick_captains(week["starting_ids"], proj)
    owned = (league_view or {}).get("owned_by_ahead") or {}
    ahead = (league_view or {}).get("rivals_ahead", 0)

    def player(pid, starting):
        return {
            "player_id": int(pid),
            "name": p["web_name"].get(pid),
            "position": config.POSITIONS.get(int(p["element_type"].get(pid, 0))),
            "team": (team_names or {}).get(int(p["team"].get(pid, 0)), "Unknown"),
            "cost_m": round(float(p["now_cost"].get(pid, 0)) / 10, 1),
            "predicted_points": round(float(proj.get(pid, 0)), 2),
            "horizon_points": round(float(p["horizon_points"].get(pid, 0)), 2),
            "starting": starting,
            "new": pid not in team_state.squad,
            "owned_by_ahead": int(owned.get(str(pid), 0)),
        }

    xi = [player(i, True) for i in week["starting_ids"]]
    bench = [player(i, False) for i in week["squad_ids"] if i not in week["starting_ids"]]
    free_week = free_plan["weeks"][0]
    return {
        "gameweek": upcoming_gw,
        "gain_six_weeks": round(planner.horizon_score(wild) - planner.horizon_score(free_plan), 1),
        "points_with": round(sum(x["predicted_points"] for x in xi) + proj.get(captain, 0), 1),
        "points_without": round(free_week["predicted_points"], 1),
        "changes": len(week["transfers_in"]),
        "xi_m": round(sum(x["cost_m"] for x in xi), 1),
        "bench_m": round(sum(x["cost_m"] for x in bench), 1),
        "bank_m": week["bank_m"],
        "captain_id": captain,
        "vice_captain_id": vice,
        "squad": xi + bench,
        "rivals_ahead": ahead,
        "free_alternative": {
            "out": [x["name"] for x in free_week["transfers_out"]],
            "in": [x["name"] for x in free_week["transfers_in"]],
        },
    }


def _plan_from_team(predictions_df, team_state, upcoming_gw):
    """Runs the weekly decision procedure (data_engine/planner.py — the same
    code the season simulator measures) and returns (result, plan), where
    result has the shape optimize_squad() returns, so everything downstream
    is indifferent to which mode produced it.

    The shipped recommendation spends free transfers only; a hit is surfaced
    as advice when its extra moves out-earn their cost over the horizon.
    """
    xp_by_gw = {
        int(row["player_id"]): {int(k): float(v) for k, v in (row["xp_by_gw"] or {}).items()}
        for _, row in predictions_df.iterrows()
    }
    gameweeks = [upcoming_gw + i for i in range(config.HORIZON_GWS)]
    decision = planner.plan_week(predictions_df, team_state, xp_by_gw, gameweeks)
    return decision["result"], decision["plan"]


def _log_summary(output: dict) -> None:
    logger.info(
        "Squad: %.1fm / %.1fm | Predicted GW%s points: %.2f",
        output["budget_used_m"], output["budget_total_m"],
        output["gameweek"], output["predicted_total_points"],
    )

    plan = output.get("transfer_plan")
    if not plan:
        return

    for week in plan["weeks"]:
        if not week["transfers_in"]:
            logger.info("  GW%-2d | no transfer (banking a free one)", week["gameweek"])
            continue
        moves = ", ".join(
            f"{out['name']} -> {inn['name']}"
            for out, inn in zip(week["transfers_out"], week["transfers_in"])
        )
        hit = f" (-{week['hit_cost']} hit)" if week["hits"] else ""
        logger.info("  GW%-2d | %s%s", week["gameweek"], moves, hit)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VAR-ified XI — FPL prediction and squad optimization engine.",
    )
    parser.add_argument(
        # Not type=int: the value can arrive as "" from an unset CI variable
        # (GitHub expands ${{ vars.FPL_TEAM_ID }} to an empty string, not to
        # nothing), and argparse would apply int("") to that default and abort
        # the whole run. Parsed by hand below instead.
        "--team-id", default=(os.environ.get("FPL_TEAM_ID") or "").strip() or None,
        help="Your FPL team id (the number in your team's public URL). With it, "
             "the engine plans transfers from the squad you actually own; "
             "without it, it builds the best possible squad from scratch.",
    )
    args = parser.parse_args()

    team_id = None
    if args.team_id not in (None, ""):
        try:
            team_id = int(args.team_id)
        except (TypeError, ValueError):
            parser.error(f"--team-id must be a number, got {args.team_id!r}")

    run_pipeline(team_id=team_id)


if __name__ == "__main__":
    main()