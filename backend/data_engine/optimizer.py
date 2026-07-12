"""
File: optimizer.py
Path: fpl-optimizer/backend/data_engine/optimizer.py

Mixed-Integer Linear Program (via PuLP/CBC) that simultaneously decides:
  1. Which 15 players make the squad (budget + position quota + club-limit constraints)
  2. Which 11 of those start (valid formation constraints)
  3. Who is captain (2x points) and vice-captain (backup 2x if captain doesn't play)

Objective: maximize predicted points of the starting XI (full weight) plus a
small weight on the bench (so bench players are at least useful fallbacks)
plus the extra points earned by the captain armband.
"""

import logging
import pulp
import pandas as pd

from config import (
    SQUAD_SIZE,
    BUDGET,
    SQUAD_POSITION_LIMITS,
    STARTING_XI_LIMITS,
    MAX_PLAYERS_PER_CLUB,
    BENCH_WEIGHT,
)

logger = logging.getLogger(__name__)


def optimize_squad(players_df: pd.DataFrame) -> dict:
    """
    players_df must contain columns:
      player_id, web_name, element_type, team, now_cost, predicted_points

    Returns a dict with squad / starting_xi / bench / captain / vice_captain
    player_ids plus summary totals.
    """
    df = players_df.dropna(subset=["predicted_points", "now_cost", "element_type", "team"]).copy()
    df["player_id"] = df["player_id"].astype(int)
    ids = df["player_id"].tolist()

    points = df.set_index("player_id")["predicted_points"].to_dict()
    cost = df.set_index("player_id")["now_cost"].to_dict()
    pos = df.set_index("player_id")["element_type"].to_dict()
    club = df.set_index("player_id")["team"].to_dict()

    prob = pulp.LpProblem("FPL_Squad_Optimization", pulp.LpMaximize)

    # Decision variables
    squad = pulp.LpVariable.dicts("squad", ids, cat="Binary")     # in 15-man squad
    starts = pulp.LpVariable.dicts("starts", ids, cat="Binary")   # in starting XI
    captain = pulp.LpVariable.dicts("captain", ids, cat="Binary") # is captain

    # A player can only start if selected, and can only be captain if starting
    for i in ids:
        prob += starts[i] <= squad[i]
        prob += captain[i] <= starts[i]

    # Exactly 15 in the squad, exactly 11 starting
    prob += pulp.lpSum(squad[i] for i in ids) == SQUAD_SIZE
    prob += pulp.lpSum(starts[i] for i in ids) == 11
    prob += pulp.lpSum(captain[i] for i in ids) == 1

    # Budget constraint (now_cost is in tenths of a million, matching BUDGET)
    prob += pulp.lpSum(cost[i] * squad[i] for i in ids) <= BUDGET

    # Exact squad position quotas (2 GK / 5 DEF / 5 MID / 3 FWD)
    for etype, quota in SQUAD_POSITION_LIMITS.items():
        prob += pulp.lpSum(squad[i] for i in ids if pos[i] == etype) == quota

    # Valid starting formation
    for etype, (lo, hi) in STARTING_XI_LIMITS.items():
        prob += pulp.lpSum(starts[i] for i in ids if pos[i] == etype) >= lo
        prob += pulp.lpSum(starts[i] for i in ids if pos[i] == etype) <= hi

    # Max players from any one real-life club
    clubs = set(club.values())
    for c in clubs:
        prob += pulp.lpSum(squad[i] for i in ids if club[i] == c) <= MAX_PLAYERS_PER_CLUB

    # Objective: starting XI at full weight + bench at reduced weight
    #            + captain bonus (extra 1x points on top of their base points)
    objective = pulp.lpSum(points[i] * starts[i] for i in ids)
    objective += pulp.lpSum(points[i] * BENCH_WEIGHT * (squad[i] - starts[i]) for i in ids)
    objective += pulp.lpSum(points[i] * captain[i] for i in ids)  # captain's 2nd multiplier
    prob += objective

    solver = pulp.PULP_CBC_CMD(msg=False)
    status = prob.solve(solver)

    if pulp.LpStatus[status] != "Optimal":
        raise RuntimeError(f"Optimizer did not find an optimal solution: {pulp.LpStatus[status]}")

    squad_ids = [i for i in ids if pulp.value(squad[i]) > 0.5]
    starting_ids = [i for i in ids if pulp.value(starts[i]) > 0.5]
    bench_ids = [i for i in squad_ids if i not in starting_ids]
    captain_id = next(i for i in ids if pulp.value(captain[i]) > 0.5)

    # Vice-captain: highest predicted points among remaining starters
    vice_candidates = [i for i in starting_ids if i != captain_id]
    vice_captain_id = max(vice_candidates, key=lambda i: points[i]) if vice_candidates else None

    total_cost = sum(cost[i] for i in squad_ids)
    starting_xi_points = sum(points[i] for i in starting_ids)
    captain_bonus = points[captain_id]
    total_predicted_points = starting_xi_points + captain_bonus

    logger.info(
        "Optimizer solved: %.1fm spent, %.2f predicted starting XI points (incl. captain)",
        total_cost / 10, total_predicted_points,
    )

    return {
        "squad_ids": squad_ids,
        "starting_ids": starting_ids,
        "bench_ids": bench_ids,
        "captain_id": captain_id,
        "vice_captain_id": vice_captain_id,
        "total_cost": total_cost,
        "total_predicted_points": round(total_predicted_points, 2),
    }
