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
    entry_data,
    fetch_data,
    feature_engineering,
    historical_data,
    injury_log,
    optimizer,
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
                      chip_advice: list = None, chip_watch: dict = None) -> dict:
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
    plan, team_state = None, None

    if team_id:
        team_state = entry_data.build_team_state(
            team_id, bootstrap, histories, upcoming_gw
        )
        result, plan = _plan_from_team(predictions_df, team_state, upcoming_gw)
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

    # 7. Write output
    output = build_output_json(bootstrap, predictions_df, result, plan=plan,
                               team_state=team_state, chip_advice=chip_advice,
                               chip_watch=chip_watch)

    config.OUTPUT_JSON_PATH.write_text(json.dumps(output, indent=2))
    config.FRONTEND_JSON_PATH.write_text(json.dumps(output, indent=2))

    logger.info("Wrote %s", config.OUTPUT_JSON_PATH)
    logger.info("Wrote %s", config.FRONTEND_JSON_PATH)
    _log_summary(output)
    logger.info("=== VAR-ified XI: decision confirmed, no VAR check needed ===")


def _horizon_score(plan: dict) -> float:
    """Decay-weighted expected points across the whole plan, hits already
    netted out. This is the single number the two plans are compared on.
    """
    return sum(config.HORIZON_DECAY ** i * w["predicted_points"]
               for i, w in enumerate(plan["weeks"]))


def _team_state_after(team_state, free_week: dict, predictions_df) -> "entry_data.TeamState":
    """A synthetic team as it would stand right after making the free plan's
    gameweek-1 moves — the starting point for asking "is one more hit worth
    it FROM HERE", rather than "what does an unrelated all-hits plan look
    like". This is what makes the follow-up solve additive instead of just
    another independent optimum that happens to also spend some hits.
    """
    costs = predictions_df.set_index("player_id")["now_cost"].to_dict()
    sell_prices = dict(team_state.sell_prices)
    for p in free_week["transfers_in"]:
        # A player bought today hasn't accrued any profit yet, so his sell
        # price is exactly his buy price (see entry_data.compute_sell_price).
        sell_prices[p["player_id"]] = round(p["cost_m"] * 10)

    remaining_free = max(0, team_state.free_transfers - free_week["transfer_count"])

    return entry_data.TeamState(
        entry_id=team_state.entry_id,
        name=team_state.name,
        gameweek=team_state.gameweek,
        squad=list(free_week["squad_ids"]),
        bank=round(free_week["bank_m"] * 10),
        squad_value=sum(costs.get(p, sell_prices.get(p, 0)) for p in free_week["squad_ids"]),
        # Free transfers the free plan chose to bank stay available here —
        # only transfers beyond those genuinely cost a hit.
        free_transfers=max(1, remaining_free),
        sell_prices=sell_prices,
        chips_used=team_state.chips_used,
        chips_available=team_state.chips_available,
    )


def _hit_recommendation(team_state, free_plan: dict, predictions_df, xp_by_gw: dict,
                        gameweeks: list) -> dict | None:
    """Decides whether a points hit this gameweek is actually worth taking —
    ON TOP OF the free plan, not instead of it.

    Re-solves from the squad the free plan would leave you with, allowing
    further hits. Because that solve starts from the free plan's own result,
    its gameweek-1 transfers ARE the exact extra moves a hit would buy — no
    guessing by diffing two unrelated optimal solutions, which can (and did)
    land on entirely different squads that merely happened to both spend
    close to the same number of transfers.
    """
    free_week = free_plan["immediate"]
    topup_state = _team_state_after(team_state, free_week, predictions_df)

    topup_plan = transfer_optimizer.plan_transfers(
        predictions_df, topup_state, xp_by_gw, gameweeks
    )
    topup_week = topup_plan["immediate"]
    if topup_week["hits"] <= 0:
        return None

    # Both solves start from the SAME real squad and cover the SAME horizon,
    # one with the extra hit-funded moves priced in (hit cost already
    # subtracted into predicted_points — see transfer_optimizer._extract_plan)
    # and one without, so this difference is a fair like-for-like gain.
    gain = _horizon_score(topup_plan) - _horizon_score(free_plan)

    return {
        "worth_it": gain > 0,
        "hit_cost": topup_week["hit_cost"],
        "net_gain_over_horizon": round(gain, 1),
        "extra_transfers_in": topup_week["transfers_in"],
        "extra_transfers_out": topup_week["transfers_out"],
        "verdict": (
            f"On top of the free transfer(s) above, taking the -{topup_week['hit_cost']} "
            f"projects {gain:+.1f} pts over {len(topup_plan['weeks'])} gameweeks after "
            "the hit — " + ("worth it." if gain > 0 else "not worth it, use free transfers only.")
        ),
    }


def _plan_from_team(predictions_df, team_state, upcoming_gw):
    """Runs the multi-gameweek transfer planner and reshapes its answer for
    the immediate gameweek into the same shape optimize_squad() returns, so
    everything downstream is indifferent to which mode produced it.

    Solves twice: a conservative plan that never takes a hit, and an
    unconstrained one. The conservative plan is what gets shipped as the
    recommendation; the hit plan is only surfaced when its extra transfers
    genuinely out-earn their -4 cost over the horizon.
    """
    xp_by_gw = {
        int(row["player_id"]): {int(k): float(v) for k, v in (row["xp_by_gw"] or {}).items()}
        for _, row in predictions_df.iterrows()
    }
    gameweeks = [upcoming_gw + i for i in range(config.HORIZON_GWS)]

    logger.info("Planning transfers across GW%d-%d (free transfers only)...",
                gameweeks[0], gameweeks[-1])
    free_plan = transfer_optimizer.plan_transfers(
        predictions_df, team_state, xp_by_gw, gameweeks, max_total_hits=0
    )

    logger.info("Checking whether a hit ON TOP of that plan is worth it...")
    hit_rec = _hit_recommendation(team_state, free_plan, predictions_df, xp_by_gw, gameweeks)
    if hit_rec and hit_rec["worth_it"]:
        logger.info("  A -%d hit IS worth taking this week: %s",
                    hit_rec["hit_cost"], hit_rec["verdict"])
    else:
        logger.info("  No hit worth taking this week — free transfers only.")

    plan = free_plan
    plan["hit_recommendation"] = hit_rec

    week = plan["immediate"]
    costs = predictions_df.set_index("player_id")["now_cost"].to_dict()
    bench_ids = [p for p in week["squad_ids"] if p not in week["starting_ids"]]

    # Captain the highest projected points in the XI. (A ceiling-based pick
    # was A/B'd and lost — see optimizer.optimize_squad.) The transfer
    # MILP's own captain variable is discarded in favour of this argmax.
    proj = predictions_df.set_index("player_id")["predicted_points"].to_dict()
    ranked = sorted(week["starting_ids"], key=lambda i: proj.get(i, 0), reverse=True)
    captain_id = ranked[0] if ranked else week["captain_id"]
    vice_captain_id = ranked[1] if len(ranked) > 1 else week["vice_captain_id"]

    result = {
        "squad_ids": week["squad_ids"],
        "starting_ids": week["starting_ids"],
        "bench_ids": bench_ids,
        "captain_id": captain_id,
        "vice_captain_id": vice_captain_id,
        "total_cost": sum(costs.get(p, 0) for p in week["squad_ids"]),
        "total_predicted_points": week["predicted_points"],
    }
    return result, plan


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