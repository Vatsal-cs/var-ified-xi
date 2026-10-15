"""
File: chip_planner.py
Path: var-ified-xi/backend/data_engine/chip_planner.py

Which week to play each chip you hold, planned together.

Every chip is worth something different in every week, and only one can be
played per week, so they're planned as one problem rather than one at a time:

  * Triple Captain adds one more copy of your best player's score that week;
  * Bench Boost adds your four bench players' scores;
  * Free Hit swaps your XI for the best one-week XI your budget can buy, for
    that week only, so it's worth that XI minus your own;
  * the Wildcard is valued separately (main._wildcard_option) — its worth is
    the transfers, which only a full replan can price.

Each week up to the chip deadline gets a value per chip, from the model's
projections for that week and the squad you'd hold then: the transfer plan's
squad for the weeks it covers, its last squad held after that. Then every way
of placing the chips in different weeks is tried and the best total wins.

Two honest limits, shown on the dashboard rather than hidden:
  * past the plan's horizon the squad is frozen, so later weeks are rough;
  * a double or blank gameweek announced later changes everything — it's read
    from the fixture list, so the plan updates the run after it appears.
"""

import itertools
import logging

import pandas as pd

import config
from data_engine import optimizer

logger = logging.getLogger(__name__)

PLANNED = ("3xc", "bboost", "freehit")
XI_LIMITS = config.STARTING_XI_LIMITS        # {element_type: (min, max)}


def best_xi(squad: list, xp: dict, pos: dict) -> tuple:
    """(starting ids, bench ids) — the highest-projected legal XI from a squad."""
    by_pos = {e: sorted((p for p in squad if pos.get(p) == e), key=lambda p: -xp.get(p, 0.0))
              for e in (1, 2, 3, 4)}
    best, best_val = None, -1.0
    (dmin, dmax), (mmin, mmax), (fmin, fmax) = XI_LIMITS[2], XI_LIMITS[3], XI_LIMITS[4]
    for d in range(dmin, dmax + 1):
        for m in range(mmin, mmax + 1):
            f = 10 - d - m
            if not fmin <= f <= fmax:
                continue
            if len(by_pos[2]) < d or len(by_pos[3]) < m or len(by_pos[4]) < f or not by_pos[1]:
                continue
            xi = by_pos[1][:1] + by_pos[2][:d] + by_pos[3][:m] + by_pos[4][:f]
            val = sum(xp.get(p, 0.0) for p in xi)
            if val > best_val:
                best, best_val = xi, val
    if best is None:
        return [], list(squad)
    return best, [p for p in squad if p not in best]


def _week_values(gw, squad, xp_gw, pos, fh_points):
    xi, bench = best_xi(squad, xp_gw, pos)
    captain = max(xi, key=lambda p: xp_gw.get(p, 0.0)) if xi else None
    xi_points = sum(xp_gw.get(p, 0.0) for p in xi) + (xp_gw.get(captain, 0.0) if captain else 0.0)
    return {
        "gameweek": gw,
        "3xc": round(xp_gw.get(captain, 0.0), 1) if captain else 0.0,
        "3xc_player": captain,
        "bboost": round(sum(xp_gw.get(p, 0.0) for p in bench), 1),
        "freehit": round(max(0.0, fh_points - xi_points), 1) if fh_points is not None else None,
        "xi_points": round(xi_points, 1),
    }


def free_hit_points(players: pd.DataFrame, xp_by_gw: dict, gameweeks: list, budget: int) -> dict:
    """{gw: XI + captain points of the best one-week squad within budget}.
    The same for every scenario — a Free Hit ignores the squad you own."""
    out = {}
    for gw in gameweeks:
        pool = players[["player_id", "web_name", "element_type", "team", "now_cost"]].copy()
        pool["predicted_points"] = pool["player_id"].map(
            lambda p: float((xp_by_gw.get(p) or {}).get(gw, 0.0)))
        pool = pool[pool["predicted_points"] > 0]
        try:
            r = optimizer.optimize_squad(pool, bench_weight=0.0, budget=budget)
            xp = pool.set_index("player_id")["predicted_points"]
            out[gw] = float(sum(xp.get(p, 0) for p in r["starting_ids"]) + xp.get(r["captain_id"], 0))
        except Exception as e:                       # one bad week shouldn't sink the plan
            logger.warning("Free Hit value for GW%d skipped: %s", gw, e)
            out[gw] = None
    return out


def assign(weeks: list, chips: list, blocked: set = frozenset()) -> list:
    """Best placement of the chips in different weeks: every placement tried
    (a handful of chips over at most ~19 weeks is a few thousand)."""
    chips = [c for c in chips if c in PLANNED]
    gws = [w["gameweek"] for w in weeks if w["gameweek"] not in blocked]
    val = {(w["gameweek"], c): (w.get(c) or 0.0) for w in weeks for c in chips}
    best, best_total = (), -1.0
    for combo in itertools.permutations(gws, len(chips)):
        total = sum(val[(gw, c)] for gw, c in zip(combo, chips))
        if total > best_total:
            best, best_total = combo, total
    return [{"chip": c, "gameweek": gw, "value": round(val[(gw, c)], 1)}
            for c, gw in zip(chips, best)]


def plan(players: pd.DataFrame, xp_by_gw: dict, gameweeks: list, chips: list,
         scenarios: dict, budget: int, fixtures_by_gw: dict = None, names: dict = None) -> dict:
    """scenarios: {key: {"label", "weeks": [{gameweek, squad_ids}], "blocked": {gw}}}
    — the squads you'd hold week by week under each choice (with or without a
    Wildcard now). Returns the chip plan for the dashboard."""
    pos = players.set_index("player_id")["element_type"].astype(int).to_dict()
    names = names or players.set_index("player_id")["web_name"].to_dict()
    fh = free_hit_points(players, xp_by_gw, gameweeks, budget) if "freehit" in chips else {}
    fixtures_by_gw = fixtures_by_gw or {}

    out = {"gameweeks": gameweeks, "chips": [c for c in chips if c in PLANNED], "scenarios": []}
    for key, sc in scenarios.items():
        planned = {w["gameweek"]: w["squad_ids"] for w in sc["weeks"]}
        firm_through = max(planned) if planned else gameweeks[0]
        squad = None
        weeks = []
        for gw in gameweeks:
            squad = planned.get(gw, squad)
            if squad is None:
                continue
            xp_gw = {p: float((xp_by_gw.get(p) or {}).get(gw, 0.0)) for p in squad}
            w = _week_values(gw, squad, xp_gw, pos, fh.get(gw))
            w["3xc_player"] = names.get(w["3xc_player"]) if w["3xc_player"] else None
            w["firm"] = gw <= firm_through
            w["fixtures"] = fixtures_by_gw.get(gw)
            weeks.append(w)
        placed = assign(weeks, chips, sc.get("blocked", set()))
        by_gw = {w["gameweek"]: w for w in weeks}
        for p in placed:
            w = by_gw[p["gameweek"]]
            p["player"] = w["3xc_player"] if p["chip"] == "3xc" else None
            p["firm"] = w["firm"]
            p["now"] = p["gameweek"] == gameweeks[0]
        out["scenarios"].append({
            "key": key,
            "label": sc["label"],
            "plan": placed,
            "total": round(sum(p["value"] for p in placed), 1),
            "weeks": weeks,
            "firm_through_gw": firm_through,
        })
    return out
