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
    chip_planner,
    chips,
    distributions,
    other_matches,
    rivals,
    team_news,
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
                      captain_override: dict = None, wildcard_option: dict = None,
                      pmfs: dict = None, captain_odds: list = None, chip_plan: dict = None,
                      news_view: dict = None, other_view: dict = None) -> dict:
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
            # The whole spread of outcomes, not just the average (distributions.py).
            "dist": distributions.payload(pmfs[pid]) if pmfs and pid in pmfs else None,
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
    if captain_odds:
        output["captain_odds"] = captain_odds
    if pmfs:
        # The page compares any two players itself (bench close calls), with
        # the same recalibration the backend uses.
        output["odds_calibration"] = {"pair_logit_scale": distributions.PAIR_LOGIT_SCALE}
    if chip_plan:
        output["chip_plan"] = chip_plan
    if news_view:
        output["team_news"] = news_view
    if other_view:
        output["other_matches"] = other_view
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

    # Cup, European and international matches as inputs — only once tested
    # in (config.OTHER_MATCHES); see data_engine/other_matches.py.
    if config.OTHER_MATCHES:
        _attach_other_matches(history_df, bootstrap)
    train_df = feature_engineering.build_training_set(history_df)
    predict_df = feature_engineering.build_prediction_set(
        bootstrap, history_df, histories, horizon=config.HORIZON_GWS
    )
    if config.OTHER_MATCHES:
        _attach_other_matches(predict_df, bootstrap)

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

    # 4. Train
    logger.info("Training 2-stage model (minutes classifier + conditional points) on %d current-season rows...", len(train_df))
    model_bundle = train_model.train_models(train_df, historical_df=historical_train_df)

    upcoming_gw = feature_engineering.next_gameweek(bootstrap)
    team_state = None
    if team_id:
        team_state = entry_data.build_team_state(team_id, bootstrap, histories, upcoming_gw)

    # What the people you're actually playing against own. Decision support
    # only — see rivals.py on why this deliberately doesn't feed the
    # optimizer. Never fatal: a league that can't be read just isn't shown.
    league_view = None
    if team_id:
        league_view = rivals.build_league_view(team_id, bootstrap, upcoming_gw)
    team_names = {t["id"]: t["name"] for t in bootstrap["teams"]}

    # 5. Predict and decide. A function, because fresh team news can change
    # the projections, and then the whole decision is made again with it.
    def decide(rows):
        # One prediction per (player, upcoming fixture), then folded back to
        # one row per player carrying both next-gameweek and whole-horizon
        # expectations.
        fixture_predictions = train_model.predict_points(model_bundle, rows, flag_counts)
        predictions_df = feature_engineering.aggregate_horizon(fixture_predictions)
        d = {"fixture_predictions": fixture_predictions, "predictions_df": predictions_df,
             "plan": None, "captain_override": None, "wildcard": None, "wildcard_plan": None}
        if team_state:
            d["result"], d["plan"] = _plan_from_team(predictions_df, team_state, upcoming_gw)
            d["captain_override"] = _apply_armband_override(d["result"], d["plan"],
                                                            predictions_df, upcoming_gw)
            # Is the Wildcard worth playing this week? Computed every refresh
            # while it's in hand, so the answer is on the dashboard without
            # anyone having to run anything.
            if "wildcard" in (team_state.chips_available or []):
                try:
                    d["wildcard"], d["wildcard_plan"] = _wildcard_option(
                        predictions_df, team_state, upcoming_gw, d["plan"], league_view, team_names)
                except Exception as e:                      # never fatal to the refresh
                    logger.warning("Wildcard check skipped: %s", e)
        else:
            logger.info("Solving MILP squad optimizer over %d available players (horizon: %d GWs)...",
                        len(predictions_df), config.HORIZON_GWS)
            d["result"] = optimizer.optimize_squad(predictions_df, objective_col="horizon_points")
        return d

    d = decide(predict_df)

    # 5b. Team news, read for the clubs this decision involves. Out/doubtful
    # calls worse than FPL's own flags re-run the decision with them.
    news, news_applied = None, []
    if team_state:
        try:
            clubs = _news_targets(d, team_state, bootstrap, fixtures, upcoming_gw)
            news = team_news.get(clubs, upcoming_gw, _deadline(bootstrap, upcoming_gw))
            news_applied = team_news.apply(predict_df, news, upcoming_gw)
            if news_applied:
                logger.info("Team news changes %d projection(s); deciding again.", len(news_applied))
                d = decide(predict_df)
        except Exception as e:                              # never fatal to the refresh
            logger.warning("Team news skipped: %s", e)

    predictions_df, result, plan = d["predictions_df"], d["result"], d["plan"]

    # 5c. A full points distribution per player, and the captaincy odds.
    pmfs, captain_odds = {}, None
    tables = distributions.load_tables()
    if tables:
        pmfs = distributions.next_gameweek_pmfs(tables, d["fixture_predictions"], upcoming_gw)
        captain_odds = _captain_odds(pmfs, result, predictions_df)

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
    chip_expiry, chip_plan = None, None
    if team_state:
        chip_expiry = chips.expiry_plan(team_state.chip_deadlines, upcoming_gw,
                                        plan, predictions_df)
        try:
            chip_plan = _chip_plan(model_bundle, flag_counts, bootstrap, history_df, histories,
                                   fixtures, team_state, upcoming_gw, d, news)
        except Exception as e:                              # never fatal to the refresh
            logger.warning("Chip plan skipped: %s", e)

    # 6d. Your players' games outside the Premier League over the planning
    # window — midweek European and cup ties, international duty. Shown
    # whatever the model does with them; never fatal.
    other_view = None
    if team_state:
        try:
            ids = list(team_state.squad)
            ids += [m["player_id"] for m in (plan or {}).get("weeks", [{}])[0].get("transfers_in", [])]
            if d["wildcard"]:
                ids += [p["player_id"] for p in d["wildcard"]["squad"]]
            end = _deadline(bootstrap, upcoming_gw + config.HORIZON_GWS)
            other_view = other_matches.view(bootstrap, ids, pd.Timestamp.now("UTC").tz_convert(None),
                                            pd.Timestamp(end).tz_convert(None))
        except Exception as e:
            logger.warning("Other matches view skipped: %s", e)

    # 7. Write output
    output = build_output_json(bootstrap, predictions_df, result, plan=plan,
                               team_state=team_state, chip_advice=chip_advice,
                               league_view=league_view,
                               chip_expiry=chip_expiry,
                               chip_watch=chip_watch,
                               captain_override=d["captain_override"],
                               wildcard_option=d["wildcard"],
                               pmfs=pmfs, captain_odds=captain_odds, chip_plan=chip_plan,
                               news_view=_news_payload(news, news_applied, d, team_state),
                               other_view=other_view)

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
                     league_view: dict = None, team_names: dict = None) -> tuple:
    """The same six-week plan with a Wildcard played this gameweek, against
    the free-transfer plan the dashboard already recommends. Returns (the
    dashboard's summary, the Wildcard plan itself)."""
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
    }, wild


def _attach_other_matches(df, bootstrap: dict) -> None:
    """other_matches inputs on this season's rows, in place; an ESPN outage
    leaves neutral values rather than stopping the refresh."""
    names = {e["id"]: f"{e['first_name']} {e['second_name']}" for e in bootstrap["elements"]}
    clubs = {t["id"]: t["name"] for t in bootstrap["teams"]}
    try:
        other_matches.attach(df, other_matches.current_season(bootstrap), names, clubs)
    except Exception as e:
        logger.warning("Other matches unavailable (%s); neutral values used", e)
        for col, v in other_matches.NEUTRAL.items():
            df[col] = v


def _deadline(bootstrap: dict, gameweek: int) -> datetime:
    for e in bootstrap["events"]:
        if e["id"] == gameweek and e.get("deadline_time"):
            return datetime.fromisoformat(e["deadline_time"].replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def _news_targets(d: dict, team_state, bootstrap: dict, fixtures: list, gameweek: int) -> list:
    """The clubs to read team news for, each with the players that matter:
    your squad, this week's planned buys, the Wildcard squad."""
    ids = set(team_state.squad)
    week = (d["plan"] or {}).get("weeks", [{}])[0]
    ids |= {m["player_id"] for m in week.get("transfers_in", [])}
    if d["wildcard"]:
        ids |= {p["player_id"] for p in d["wildcard"]["squad"]}
    els = {e["id"]: e for e in bootstrap["elements"]}
    teams = {t["id"]: t["name"] for t in bootstrap["teams"]}
    matches = {}
    for f in fixtures:
        if f.get("event") != gameweek:
            continue
        when = (f.get("kickoff_time") or "")[:16].replace("T", " ")
        matches.setdefault(f["team_h"], []).append(f"home vs {teams.get(f['team_a'])}, {when} UTC")
        matches.setdefault(f["team_a"], []).append(f"away at {teams.get(f['team_h'])}, {when} UTC")
    clubs = {}
    for pid in ids:
        e = els.get(pid)
        if not e or e["team"] not in matches:          # no match this week: nothing to read
            continue
        c = clubs.setdefault(e["team"], {"club": teams[e["team"]],
                                         "fixture": "; ".join(matches[e["team"]]), "players": []})
        c["players"].append({"player_id": pid, "name": f"{e['first_name']} {e['second_name']}",
                             "position": config.POSITIONS.get(e["element_type"])})
    return sorted(clubs.values(), key=lambda c: c["club"])


def _news_payload(news: dict, applied: list, d: dict, team_state) -> dict | None:
    """What the dashboard shows: calls about the players in this decision,
    worst first, and which of them moved a projection."""
    if not team_state:
        return None
    if not news:
        return {"enabled": team_news.enabled(), "items": [], "applied": []}
    ids = set(team_state.squad)
    week = (d["plan"] or {}).get("weeks", [{}])[0]
    ids |= {m["player_id"] for m in week.get("transfers_in", [])}
    if d["wildcard"]:
        ids |= {p["player_id"] for p in d["wildcard"]["squad"]}
    order = {s: i for i, s in enumerate(team_news.STATUSES)}
    items = [i for i in news.get("items", [])
             if i.get("player_id") in ids or i.get("status") in team_news.APPLIED]
    items.sort(key=lambda i: (order.get(i["status"], 9), i["name"]))
    return {"enabled": team_news.enabled(), "fetched_at": news.get("fetched_at"),
            "model": news.get("model"), "items": items, "applied": applied,
            "errors": len(news.get("errors", []))}


def _captain_odds(pmfs: dict, result: dict, predictions_df) -> list:
    """The armband as head-to-heads: the captain, then the XI's next three
    best projections, each with how often he'd outscore the captain (ties
    left out, recalibrated) and his chance of 10+."""
    proj = predictions_df.set_index("player_id")["predicted_points"].to_dict()
    names = predictions_df.set_index("player_id")["web_name"].to_dict()
    cap = result["captain_id"]
    if cap not in pmfs:
        return []
    others = sorted((p for p in result["starting_ids"] if p in pmfs and p != cap),
                    key=lambda p: -proj.get(p, 0))[:3]
    rows = []
    for p in [cap] + others:
        s = distributions.summary(pmfs[p])
        rows.append({"player_id": int(p), "name": names.get(p),
                     "projected": round(float(proj.get(p, 0)), 2),
                     "p_haul": s["p_haul"], "p10": s["p10"], "p90": s["p90"],
                     "beats_captain": None if p == cap else
                     round(distributions.head_to_head(pmfs[p], pmfs[cap]), 3)})
    return rows


def _chip_plan(model_bundle, flag_counts, bootstrap, history_df, histories, fixtures,
               team_state, upcoming_gw, d, news) -> dict | None:
    """Every chip you hold placed in its best week up to its deadline, with and
    without a Wildcard now (data_engine/chip_planner.py)."""
    held = [c for c in team_state.chips_available if c in chip_planner.PLANNED]
    if not held:
        return None
    deadline = min(team_state.chip_deadlines[c] for c in held)
    held = [c for c in held if team_state.chip_deadlines[c] == deadline]
    gameweeks = list(range(upcoming_gw, deadline + 1))
    if not gameweeks:
        return None

    # Projections out to the chip deadline: the same model, the same frozen
    # form, each week's own fixtures (and the same team news).
    rows = feature_engineering.build_prediction_set(bootstrap, history_df, histories,
                                                    horizon=len(gameweeks))
    if config.OTHER_MATCHES:
        _attach_other_matches(rows, bootstrap)
    team_news.apply(rows, news, upcoming_gw)
    long = feature_engineering.aggregate_horizon(
        train_model.predict_points(model_bundle, rows, flag_counts))
    xp = {int(r.player_id): {int(k): float(v) for k, v in (r.xp_by_gw or {}).items()}
          for r in long.itertuples()}

    scenarios = {"free": {"label": "Without the Wildcard", "weeks": d["plan"]["weeks"]}}
    if d["wildcard_plan"]:
        scenarios["wildcard"] = {"label": "With the Wildcard now", "weeks": d["wildcard_plan"]["weeks"],
                                 "blocked": {upcoming_gw}}
    counts = chips.fixture_counts_by_gameweek(fixtures, upcoming_gw, len(gameweeks))
    n_teams = len(bootstrap["teams"])
    fixtures_by_gw = {gw: {"doubles": sum(1 for n in counts.get(gw, {}).values() if n >= 2),
                           "blanks": n_teams - len(counts.get(gw, {}))} for gw in gameweeks}
    out = chip_planner.plan(long, xp, gameweeks, held, scenarios,
                            budget=team_state.squad_value + team_state.bank,
                            fixtures_by_gw=fixtures_by_gw)
    out["deadline_gw"] = deadline
    return out


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