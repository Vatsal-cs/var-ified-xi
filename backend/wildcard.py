"""
File: wildcard.py
Path: var-ified-xi/backend/wildcard.py

Is a Wildcard worth playing this week, and what squad should it build?

Builds the plan two ways from your real team — your sell prices, bank and free
transfers — and the same projections the dashboard uses:

  * free transfers only (what the dashboard recommends without a chip);
  * a Wildcard this gameweek: every transfer free, the bank of free transfers
    kept for next week, then normal weeks after it.

Both are scored on the same six-week, decay-weighted objective, so the gap is
what the Wildcard is worth over the planning horizon. It doesn't count what a
Wildcard kept for later might be worth — weigh that yourself (the first-half
Wildcard expires at the GW19 deadline either way).

Rival ownership (--league) is shown for information only. It never touches
the optimizer, which picks purely from the model's own projections: matching a
rival's pick is fine when the numbers say so, and the differentials — picks
the managers above you don't have — are where places are gained.

Usage (from backend/):
    python wildcard.py --team-id 9927826
    python wildcard.py --team-id 9927826 --league 928777 --top 4
"""

import argparse
import logging

import pandas as pd

import config
from data_engine import (entry_data, feature_engineering, fetch_data, historical_data,
                         injury_log, planner, rivals, train_model, transfer_optimizer)

logger = logging.getLogger("wildcard")


def _projections(bootstrap):
    fixtures = fetch_data.fetch_fixtures()
    histories = fetch_data.fetch_all_player_histories([p["id"] for p in bootstrap["elements"]])
    history = feature_engineering.add_rolling_features(
        feature_engineering.build_gameweek_history_df(bootstrap, histories, fixtures=fixtures))
    train = feature_engineering.build_training_set(history)
    predict = feature_engineering.build_prediction_set(bootstrap, history, histories,
                                                       horizon=config.HORIZON_GWS)
    past = feature_engineering.build_training_set(feature_engineering.add_rolling_features(
        historical_data.build_historical_training_df()))
    bundle = train_model.train_models(train, historical_df=past, save=False)
    preds = feature_engineering.aggregate_horizon(
        train_model.predict_points(bundle, predict, injury_log.get_flag_counts()))
    return preds, histories


def compare(team_id: int, bench_weight: float = None) -> dict:
    bootstrap = fetch_data.fetch_bootstrap_static()
    preds, histories = _projections(bootstrap)
    gw = feature_engineering.next_gameweek(bootstrap)
    team = entry_data.build_team_state(team_id, bootstrap, histories, gw)
    xp = {int(r.player_id): {int(k): float(v) for k, v in (r.xp_by_gw or {}).items()}
          for r in preds.itertuples()}
    gameweeks = [gw + i for i in range(config.HORIZON_GWS)]

    free = transfer_optimizer.plan_transfers(preds, team, xp, gameweeks, max_total_hits=0,
                                             bench_weight=bench_weight)
    wild = transfer_optimizer.plan_transfers(preds, team, xp, gameweeks, max_total_hits=0,
                                             bench_weight=bench_weight, wildcard=True)
    return {"gameweek": gw, "team": team, "preds": preds, "free": free, "wildcard": wild,
            "gain": planner.horizon_score(wild) - planner.horizon_score(free)}


def rival_ownership(league_id: int, top: int, me: int, gameweek: int) -> tuple:
    """({player id: how many of the league's top managers own him}, n). Read
    from their latest published picks; display only."""
    rows = rivals.fetch_standings(league_id)["standings"]["results"]
    managers = [r["entry"] for r in rows if r["entry"] != me][:top]
    counts = {}
    for entry in managers:
        try:
            picks = entry_data.fetch_picks(entry, gameweek - 1)["picks"]
        except Exception:
            continue
        for p in picks:
            counts[p["element"]] = counts.get(p["element"], 0) + 1
    return counts, len(managers)


def _describe(plan_week, preds, team, label, owned=None, n_rivals=0):
    p = preds.set_index("player_id")
    pos = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    xi, bench = plan_week["starting_ids"], [i for i in plan_week["squad_ids"]
                                           if i not in plan_week["starting_ids"]]
    proj = p["predicted_points"]
    captain, vice = planner.pick_captains(xi, proj.to_dict())
    print(f"\n{label}: GW{plan_week['gameweek']} XI projects "
          f"{sum(proj.get(i, 0) for i in xi) + proj.get(captain, 0):.1f} (captain {p['web_name'].get(captain)})")
    for title, ids in (("XI", xi), ("bench", bench)):
        rows = sorted(ids, key=lambda i: (p["element_type"].get(i, 9), -proj.get(i, 0)))
        cost = sum(p["now_cost"].get(i, 0) for i in ids) / 10
        print(f"  {title} (£{cost:.1f}m):")
        for i in rows:
            mark = "" if i in team.squad else "  NEW"
            if owned is not None:
                k = owned.get(i, 0)
                mark += f"  rivals {k}/{n_rivals}" + ("  DIFFERENTIAL" if k == 0 else "")
            print(f"    {pos.get(p['element_type'].get(i), '?'):<4}{p['web_name'].get(i, i):<16}"
                  f"£{p['now_cost'].get(i, 0) / 10:<5} next {proj.get(i, 0):4.1f}  "
                  f"6-wk {p['horizon_points'].get(i, 0):5.1f}{mark}")


def main():
    parser = argparse.ArgumentParser(description="Wildcard this week, or not?")
    parser.add_argument("--team-id", type=int, required=True)
    parser.add_argument("--bench-weight", type=float, default=None,
                        help="defaults to config.BENCH_WEIGHT")
    parser.add_argument("--league", type=int, default=None,
                        help="mini-league id: show how many of its top managers own each pick")
    parser.add_argument("--top", type=int, default=4,
                        help="how many managers above you to compare with (default 4)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    r = compare(args.team_id, args.bench_weight)
    w0 = r["wildcard"]["weeks"][0]
    sold = [o["name"] for o in w0["transfers_out"]]
    bought = [o["name"] for o in w0["transfers_in"]]
    print(f"GW{r['gameweek']} — six-week score: free transfers "
          f"{planner.horizon_score(r['free']):.1f}, Wildcard {planner.horizon_score(r['wildcard']):.1f} "
          f"-> Wildcard worth {r['gain']:+.1f} points over the horizon")
    print(f"Wildcard makes {len(sold)} changes. Out: {', '.join(sold)}. In: {', '.join(bought)}. "
          f"Bank after: £{w0['bank_m']:.1f}m")
    owned, n = (rival_ownership(args.league, args.top, args.team_id, r["gameweek"])
                if args.league else (None, 0))
    _describe(r["free"]["weeks"][0], r["preds"], r["team"], "WITHOUT the Wildcard", owned, n)
    _describe(w0, r["preds"], r["team"], "WITH the Wildcard", owned, n)
    if owned is not None:
        names = r["preds"].set_index("player_id")["web_name"]
        common = [names.get(i, i) for i, k in sorted(owned.items(), key=lambda kv: -kv[1])
                  if k >= max(2, n // 2 + 1) and i not in w0["squad_ids"]]
        print(f"\nOwned by most of the top {n} but not in the Wildcard squad: {', '.join(map(str, common)) or 'none'}")


if __name__ == "__main__":
    main()
