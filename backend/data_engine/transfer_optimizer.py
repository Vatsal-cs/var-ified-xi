"""
File: transfer_optimizer.py
Path: var-ified-xi/backend/data_engine/transfer_optimizer.py

Multi-gameweek transfer planner: a Mixed-Integer Linear Program that starts
from the squad you actually own and decides, for each of the next few
gameweeks at once, who to sell, who to buy, who to start, and who to captain.

This is the difference between a tool that says "here is a lovely £100m squad"
and one you can act on. Real FPL gives you one free transfer per gameweek
(bankable to five) and charges four points for each extra, so the question is
never "what is the best squad" — it's "what is the best *sequence of changes*
to the squad I have, given what those changes cost".

Planning several gameweeks at once is what makes the answer trustworthy. A
one-week solver will happily sell a player to chase a single good fixture; a
multi-week one sees that you'd have to sell him straight back, and declines.
It also lets the solver deliberately bank a transfer this week to afford two
next week — a move no greedy weekly optimizer can ever find.

Everything is modelled in tenths of a million, matching FPL's own prices.
"""

import logging

import pandas as pd
import pulp

from config import (
    SQUAD_SIZE,
    SQUAD_POSITION_LIMITS,
    STARTING_XI_LIMITS,
    MAX_PLAYERS_PER_CLUB,
    MAX_FREE_TRANSFERS,
    TRANSFER_HIT_COST,
    BENCH_WEIGHT,
    HORIZON_DECAY,
    SOLVER_TIME_LIMIT,
    CANDIDATE_POOL_PER_POSITION,
    HIT_MARGIN,
)

logger = logging.getLogger(__name__)


def build_candidate_pool(players_df: pd.DataFrame, must_include: list) -> pd.DataFrame:
    """Trims the player pool to a tractable size for the MILP.

    Six gameweeks times six hundred players times five binary decisions is a
    problem CBC will chew on for a very long time to tell us something we
    already know: that the 400th-best midfielder is not going in the squad.
    Keeping the best few per position plus everyone you already own loses
    nothing real — a player outside this set was never going to be bought.
    """
    keep = []
    for etype, n in CANDIDATE_POOL_PER_POSITION.items():
        pool = players_df[players_df["element_type"] == etype]
        keep.append(pool.nlargest(n, "horizon_points"))

    owned = players_df[players_df["player_id"].isin(must_include)]
    candidates = pd.concat(keep + [owned]).drop_duplicates("player_id")

    missing = set(must_include) - set(candidates["player_id"])
    if missing:
        # A player you own who has no prediction row at all (left the league,
        # say). They can still be sold, so they must exist in the model.
        logger.warning("%d owned player(s) have no prediction and will be "
                       "valued at zero points: %s", len(missing), sorted(missing))

    logger.info("Candidate pool: %d players (from %d)", len(candidates), len(players_df))
    return candidates


def plan_transfers(
    players_df: pd.DataFrame,
    team_state,
    xp_by_gw: dict,
    gameweeks: list,
    free_hit_gw: int = None,
    max_total_hits: int = None,
) -> dict:
    """Solves the multi-gameweek transfer problem.

    players_df: one row per player, needs player_id, element_type, team,
                now_cost, predicted_points, horizon_points.
    team_state: entry_data.TeamState — your current squad, bank and transfers.
    xp_by_gw:   {player_id: {gameweek: expected points}}.
    gameweeks:  the gameweeks to plan across, in order.
    max_total_hits: hard cap on point-hits across the whole horizon.
                Pass 0 for a plan that only ever spends free transfers;
                leave None to let the solver take a hit whenever it
                clears its cost by HIT_MARGIN.

    Returns the full plan: transfers per gameweek, the resulting squad, and
    the starting XI and captain for the immediate gameweek.
    """
    owned = list(team_state.squad)
    df = build_candidate_pool(players_df, owned).copy()
    df["player_id"] = df["player_id"].astype(int)

    ids = df["player_id"].tolist()
    for pid in owned:
        if pid not in ids:
            ids.append(pid)

    pos = df.set_index("player_id")["element_type"].to_dict()
    club = df.set_index("player_id")["team"].to_dict()
    buy_price = df.set_index("player_id")["now_cost"].to_dict()

    # Players you own but have no data for: they occupy a squad slot and can
    # be sold, but contribute nothing. Defaults keep the model well-formed.
    for pid in ids:
        pos.setdefault(pid, 3)
        club.setdefault(pid, 0)
        buy_price.setdefault(pid, team_state.sell_prices.get(pid, 0))

    def xp(pid, gw):
        return float(xp_by_gw.get(pid, {}).get(gw, 0.0))

    # You sell at your own selling price; you buy at the market price.
    sell_price = {pid: team_state.sell_prices.get(pid, buy_price.get(pid, 0)) for pid in ids}

    prob = pulp.LpProblem("FPL_Transfer_Plan", pulp.LpMaximize)

    squad, start, cap, vice, buy, sell = {}, {}, {}, {}, {}, {}
    for t in gameweeks:
        for i in ids:
            squad[i, t] = pulp.LpVariable(f"squad_{i}_{t}", cat="Binary")
            start[i, t] = pulp.LpVariable(f"start_{i}_{t}", cat="Binary")
            cap[i, t] = pulp.LpVariable(f"cap_{i}_{t}", cat="Binary")
            vice[i, t] = pulp.LpVariable(f"vice_{i}_{t}", cat="Binary")
            buy[i, t] = pulp.LpVariable(f"buy_{i}_{t}", cat="Binary")
            sell[i, t] = pulp.LpVariable(f"sell_{i}_{t}", cat="Binary")

    # Transfer bookkeeping, per gameweek.
    transfers = {t: pulp.LpVariable(f"transfers_{t}", lowBound=0, cat="Integer") for t in gameweeks}
    hits = {t: pulp.LpVariable(f"hits_{t}", lowBound=0, cat="Integer") for t in gameweeks}
    free = {t: pulp.LpVariable(f"free_{t}", lowBound=1, upBound=MAX_FREE_TRANSFERS,
                               cat="Integer") for t in gameweeks}
    bank = {t: pulp.LpVariable(f"bank_{t}", lowBound=0, cat="Continuous") for t in gameweeks}

    previous_squad = {i: (1 if i in owned else 0) for i in ids}
    previous_bank = team_state.bank

    for idx, t in enumerate(gameweeks):
        # --- Squad continuity: this week's squad is last week's, plus buys,
        #     minus sells. This single constraint is what ties the gameweeks
        #     together into a plan instead of independent solves. ---
        for i in ids:
            if idx == 0:
                prob += squad[i, t] == previous_squad[i] + buy[i, t] - sell[i, t]
            else:
                prev = gameweeks[idx - 1]
                prob += squad[i, t] == squad[i, prev] + buy[i, t] - sell[i, t]
            # You cannot buy someone you already have, or sell someone you don't.
            prob += buy[i, t] + sell[i, t] <= 1

        prob += pulp.lpSum(squad[i, t] for i in ids) == SQUAD_SIZE

        for etype, quota in SQUAD_POSITION_LIMITS.items():
            prob += pulp.lpSum(squad[i, t] for i in ids if pos[i] == etype) == quota

        for c in set(club.values()):
            prob += pulp.lpSum(squad[i, t] for i in ids if club[i] == c) <= MAX_PLAYERS_PER_CLUB

        # --- Starting XI, captain, vice ---
        for i in ids:
            prob += start[i, t] <= squad[i, t]
            prob += cap[i, t] <= start[i, t]
            prob += vice[i, t] <= start[i, t]
            prob += cap[i, t] + vice[i, t] <= 1

        prob += pulp.lpSum(start[i, t] for i in ids) == 11
        prob += pulp.lpSum(cap[i, t] for i in ids) == 1
        prob += pulp.lpSum(vice[i, t] for i in ids) == 1

        for etype, (lo, hi) in STARTING_XI_LIMITS.items():
            prob += pulp.lpSum(start[i, t] for i in ids if pos[i] == etype) >= lo
            prob += pulp.lpSum(start[i, t] for i in ids if pos[i] == etype) <= hi

        # --- Money ---
        proceeds = pulp.lpSum(sell_price[i] * sell[i, t] for i in ids)
        spend = pulp.lpSum(buy_price[i] * buy[i, t] for i in ids)
        prob += bank[t] == (previous_bank if idx == 0 else bank[gameweeks[idx - 1]]) + proceeds - spend

        # --- Transfers, free transfers and hits ---
        prob += transfers[t] == pulp.lpSum(buy[i, t] for i in ids)
        prob += hits[t] >= transfers[t] - free[t]

        if idx == 0:
            prob += free[t] == team_state.free_transfers
        else:
            prev = gameweeks[idx - 1]
            used = transfers[prev] - hits[prev]
            # free[t] <= free[prev] - used + 1, capped at MAX by the variable's
            # own upper bound. The solver has every incentive to take the
            # largest value allowed, since free transfers only ever relax it.
            prob += free[t] <= free[prev] - used + 1

    if max_total_hits is not None:
        prob += pulp.lpSum(hits[t] for t in gameweeks) <= max_total_hits

    # --- Objective ---
    # Points from the XI, doubled for the captain, plus a little credit for
    # bench strength (they score when a starter doesn't play). Later gameweeks
    # are discounted: a projection five weeks out is a weaker claim than one
    # for Saturday, and you'll get to revise it before then anyway.
    objective = []
    for idx, t in enumerate(gameweeks):
        weight = HORIZON_DECAY ** idx
        for i in ids:
            points = xp(i, t)
            objective.append(weight * points * start[i, t])
            objective.append(weight * points * cap[i, t])
            objective.append(weight * BENCH_WEIGHT * points * (squad[i, t] - start[i, t]))
        objective.append(-weight * (TRANSFER_HIT_COST + HIT_MARGIN) * hits[t])

    prob += pulp.lpSum(objective)

    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=SOLVER_TIME_LIMIT)
    status = prob.solve(solver)
    status_name = pulp.LpStatus[status]

    if status_name not in ("Optimal", "Not Solved"):
        raise RuntimeError(f"Transfer planner failed: {status_name}")
    if status_name != "Optimal":
        logger.warning(
            "Solver hit the %ds time limit and returned its best plan so far "
            "rather than a proven optimum.", SOLVER_TIME_LIMIT,
        )

    return _extract_plan(gameweeks, ids, squad, start, cap, vice, buy, sell,
                         transfers, hits, free, bank, xp, df, team_state)


def _chosen(var_dict, ids, t):
    return [i for i in ids if var_dict[i, t].value() and var_dict[i, t].value() > 0.5]


def _extract_plan(gameweeks, ids, squad, start, cap, vice, buy, sell,
                  transfers, hits, free, bank, xp, df, team_state) -> dict:
    """Turns the solved variables back into a readable plan."""
    names = df.set_index("player_id")["web_name"].to_dict()
    costs = df.set_index("player_id")["now_cost"].to_dict()

    weeks = []
    for t in gameweeks:
        bought = _chosen(buy, ids, t)
        sold = _chosen(sell, ids, t)
        starters = _chosen(start, ids, t)
        captains = _chosen(cap, ids, t)
        vices = _chosen(vice, ids, t)
        squad_ids = _chosen(squad, ids, t)

        n_hits = int(round(hits[t].value() or 0))
        weeks.append({
            "gameweek": t,
            "transfers_in": [
                {"player_id": i, "name": names.get(i, str(i)),
                 "cost_m": round(costs.get(i, 0) / 10, 1),
                 "predicted_points": round(xp(i, t), 2)}
                for i in bought
            ],
            "transfers_out": [
                {"player_id": i, "name": names.get(i, str(i)),
                 "sell_price_m": round(team_state.sell_prices.get(i, 0) / 10, 1),
                 "predicted_points": round(xp(i, t), 2)}
                for i in sold
            ],
            "transfer_count": int(round(transfers[t].value() or 0)),
            "free_transfers": int(round(free[t].value() or 0)),
            "hits": n_hits,
            "hit_cost": n_hits * TRANSFER_HIT_COST,
            "bank_m": round((bank[t].value() or 0) / 10, 1),
            "squad_ids": squad_ids,
            "starting_ids": starters,
            "captain_id": captains[0] if captains else None,
            "vice_captain_id": vices[0] if vices else None,
            "predicted_points": round(
                sum(xp(i, t) for i in starters)
                + (xp(captains[0], t) if captains else 0)
                - n_hits * TRANSFER_HIT_COST,
                2,
            ),
        })

    return {"weeks": weeks, "immediate": weeks[0] if weeks else None}
