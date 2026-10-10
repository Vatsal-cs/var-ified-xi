"""
File: planner.py
Path: var-ified-xi/backend/data_engine/planner.py

The weekly decision procedure that ships, in one place.

main.py runs this to produce the recommendation on the dashboard, and
season_sim.py runs the SAME function to measure it. They used to be separate:
production solved a zero-hit plan and then asked whether one more hit on top
was worth it, while the simulator let the solver plan hits in any week and
took them automatically, with the solver's arbitrary vice-captain. Results
from that simulator described a procedure nobody ran. Sharing the code makes
"what the harness measured" and "what you were told to do" the same thing by
construction.

The procedure:

  1. Plan the horizon using free transfers only.
  2. From the squad that plan leaves, re-solve allowing hits. If the extra
     moves out-earn their cost over the horizon, advise the hit.
  3. Captain the highest next-gameweek projection in the XI, vice the second.
     The MILP's own armband variables are discarded: the vice has no weight
     in its objective, so its pick there is arbitrary.
"""

import logging

import config
from data_engine import entry_data, transfer_optimizer

logger = logging.getLogger(__name__)


def horizon_score(plan: dict) -> float:
    """Decay-weighted expected points across the whole plan, hits already
    netted out. This is the single number the two plans are compared on.
    """
    return sum(config.HORIZON_DECAY ** i * w["predicted_points"]
               for i, w in enumerate(plan["weeks"]))


def pick_captains(starting_ids: list, values: dict) -> tuple:
    """(captain, vice): the two highest values in the XI."""
    ranked = sorted(starting_ids, key=lambda i: values.get(i, 0), reverse=True)
    return (ranked[0] if ranked else None,
            ranked[1] if len(ranked) > 1 else None)


def team_state_after(team_state, free_week: dict, players_df) -> "entry_data.TeamState":
    """A synthetic team as it would stand right after making the free plan's
    gameweek-1 moves — the starting point for asking "is one more hit worth
    it FROM HERE", rather than "what does an unrelated all-hits plan look
    like". This is what makes the follow-up solve additive instead of just
    another independent optimum that happens to also spend some hits.
    """
    costs = players_df.set_index("player_id")["now_cost"].to_dict()
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
        # only transfers beyond those genuinely cost a hit. This can be zero,
        # and must be allowed to be: rounding it up to one handed the hit check
        # a free transfer that doesn't exist.
        free_transfers=remaining_free,
        sell_prices=sell_prices,
        chips_used=team_state.chips_used,
        chips_available=team_state.chips_available,
        chip_deadlines=team_state.chip_deadlines,
    )


def hit_check(team_state, free_plan: dict, players_df, xp_by_gw: dict,
              gameweeks: list, hit_margin: float = None, rules=None,
              bench_weight: float = None):
    """Decides whether a points hit this gameweek is actually worth taking —
    ON TOP OF the free plan, not instead of it.

    Re-solves from the squad the free plan would leave you with, allowing
    further hits. Because that solve starts from the free plan's own result,
    its gameweek-1 transfers ARE the exact extra moves a hit would buy — no
    guessing by diffing two unrelated optimal solutions, which can (and did)
    land on entirely different squads that merely happened to both spend
    close to the same number of transfers.

    Returns (recommendation for the dashboard or None, the hit week itself
    or None). The week is what a manager following the advice would field.
    """
    free_week = free_plan["immediate"]
    topup_state = team_state_after(team_state, free_week, players_df)

    topup_plan = transfer_optimizer.plan_transfers(
        players_df, topup_state, xp_by_gw, gameweeks,
        hit_margin=hit_margin, rules=rules, bench_weight=bench_weight,
    )
    topup_week = topup_plan["immediate"]
    if topup_week["hits"] <= 0:
        return None, None

    # Both solves start from the SAME real squad and cover the SAME horizon,
    # one with the extra hit-funded moves priced in (hit cost already
    # subtracted into predicted_points — see transfer_optimizer._extract_plan)
    # and one without, so this difference is a fair like-for-like gain.
    gain = horizon_score(topup_plan) - horizon_score(free_plan)

    recommendation = {
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
    return recommendation, (topup_week if gain > 0 else None)


def plan_week(players_df, team_state, xp_by_gw: dict, gameweeks: list,
              hit_margin: float = None, captain_col: str = "predicted_points",
              rules=None, bench_weight: float = None) -> dict:
    """Production's full weekly decision.

    players_df: one row per player with now_cost, predicted_points (next
                gameweek), horizon_points and, if captaining on something
                else, `captain_col`.
    hit_margin: overrides config.HIT_MARGIN in the hit check. Research knob.
    rules:      rules.SeasonRules for a replayed season; None is today's.

    Returns {"result", "plan", "hit_week"}. `result` has the same shape as
    optimizer.optimize_squad()'s, for the free plan. `hit_week` is the week
    a manager following a "hit worth it" verdict would field, else None.
    """
    logger.info("Planning transfers across GW%d-%d (free transfers only)...",
                gameweeks[0], gameweeks[-1])
    free_plan = transfer_optimizer.plan_transfers(
        players_df, team_state, xp_by_gw, gameweeks, max_total_hits=0, rules=rules,
        bench_weight=bench_weight,
    )

    logger.info("Checking whether a hit ON TOP of that plan is worth it...")
    hit_rec, hit_week = hit_check(team_state, free_plan, players_df, xp_by_gw,
                                  gameweeks, hit_margin=hit_margin, rules=rules,
                                  bench_weight=bench_weight)
    if hit_rec and hit_rec["worth_it"]:
        logger.info("  A -%d hit IS worth taking this week: %s",
                    hit_rec["hit_cost"], hit_rec["verdict"])
    else:
        logger.info("  No hit worth taking this week — free transfers only.")

    plan = free_plan
    plan["hit_recommendation"] = hit_rec

    week = plan["immediate"]
    costs = players_df.set_index("player_id")["now_cost"].to_dict()
    values = players_df.set_index("player_id")[captain_col].to_dict()
    captain_id, vice_captain_id = pick_captains(week["starting_ids"], values)

    result = {
        "squad_ids": week["squad_ids"],
        "starting_ids": week["starting_ids"],
        "bench_ids": [p for p in week["squad_ids"] if p not in week["starting_ids"]],
        "captain_id": captain_id if captain_id is not None else week["captain_id"],
        "vice_captain_id": (vice_captain_id if vice_captain_id is not None
                            else week["vice_captain_id"]),
        "total_cost": sum(costs.get(p, 0) for p in week["squad_ids"]),
        "total_predicted_points": week["predicted_points"],
    }
    return {"result": result, "plan": plan, "hit_week": hit_week}
