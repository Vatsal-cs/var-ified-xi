"""
File: rivals.py
Path: var-ified-xi/backend/data_engine/rivals.py

What the people you're actually playing against own.

Global ownership — the `selected_by_percent` in every FPL payload — is close to
useless for winning a mini-league. What decides whether a transfer gains you a
PLACE is ownership inside your own league, and those are very different
numbers: a player owned by 8% of the world can be owned by half your league.

The arithmetic that makes this worth showing: your position relative to a rival
moves by (your points from a player) minus (theirs). Points you BOTH scored
cancel out entirely. So a haul from someone everyone in the league owns keeps
you exactly where you were, while the same haul from a player nobody else has
moves you past all of them.

This is deliberately decision support and NOT an optimizer objective. Tilting
the solver toward low-ownership players was tested (season_sim.py's
differential policies) and came out roughly points-neutral — it buys rank
variance at the cost of expected points, which is the right trade only when
you're behind and need to catch someone. That's a judgement about your
situation, not something a solver should quietly make on your behalf. So the
numbers go on the dashboard and the call stays yours.

Everything here uses public, unauthenticated endpoints.
"""

import logging

import requests

import config
from data_engine.entry_data import _get, fetch_entry, fetch_picks

logger = logging.getLogger(__name__)

# Above this many members a league stops being a mini-league you can read
# player-by-player and becomes a global one where per-rival picks are neither
# fetchable nor meaningful.
MAX_LEAGUE_SIZE = 200

# Hard cap on per-rival requests, so a mid-size league can't turn one run into
# hundreds of API calls.
MAX_RIVALS = 50

# A player held by at least this share of the league is "template": owning him
# wins you nothing, and NOT owning him is a risk rather than a differential.
TEMPLATE_THRESHOLD = 0.5

# At or below this share he's a genuine differential.
DIFFERENTIAL_THRESHOLD = 0.34


def fetch_standings(league_id: int) -> dict:
    return _get(f"leagues-classic/{league_id}/standings/")


def pick_league(entry: dict) -> dict:
    """The mini-league worth analysing, from all the ones you're in.

    An FPL account is auto-joined to several huge leagues — overall, your
    country, your club, the gameweek you started. The one you actually care
    about is the small one you were invited to, so this takes the smallest
    that's still under MAX_LEAGUE_SIZE. An explicit config.RIVAL_LEAGUE_ID
    overrides the guess.
    """
    classic = (entry.get("leagues") or {}).get("classic") or []
    if not classic:
        return None

    if config.RIVAL_LEAGUE_ID:
        for league in classic:
            if league["id"] == config.RIVAL_LEAGUE_ID:
                return league
        logger.warning("RIVAL_LEAGUE_ID %s is not a league this entry is in; "
                       "falling back to the smallest.", config.RIVAL_LEAGUE_ID)

    small = [L for L in classic
             if L.get("rank_count") and L["rank_count"] <= MAX_LEAGUE_SIZE]
    if not small:
        return None
    return min(small, key=lambda L: L["rank_count"])


def build_league_view(entry_id: int, bootstrap: dict, gameweek: int) -> dict:
    """Ownership and chip state across your mini-league.

    gameweek is the one being planned FOR, so picks are read from the
    gameweek before it — the most recent one FPL has published.
    """
    try:
        entry = fetch_entry(entry_id)
        league = pick_league(entry)
        if not league:
            logger.info("No mini-league small enough to analyse — skipping "
                        "the rival view.")
            return None

        standings = fetch_standings(league["id"])
        rows = (standings.get("standings") or {}).get("results") or []
        if not rows:
            return None

        last_played = max(1, gameweek - 1)
        names = {p["id"]: p["web_name"] for p in bootstrap["elements"]}
        costs = {p["id"]: p["now_cost"] / 10 for p in bootstrap["elements"]}

        me = next((r for r in rows if r["entry"] == entry_id), None)
        my_rank = me["rank"] if me else None

        squads, chips, failed = {}, {}, 0
        for row in rows[:MAX_RIVALS]:
            try:
                picks = fetch_picks(row["entry"], last_played)
            except requests.RequestException:
                failed += 1
                continue
            # Starters only. A player on someone's bench didn't score for
            # them, so he isn't part of the gap between you.
            squads[row["entry"]] = [
                p["element"] for p in picks["picks"] if p["position"] <= 11
            ]
            chips[row["entry"]] = picks.get("active_chip")

        if failed:
            logger.warning("Could not read picks for %d rival(s); ownership "
                           "figures are over the rest.", failed)

        mine = set(squads.get(entry_id, []))
        # Rivals AHEAD of you are the ones you have to actually pass, so
        # ownership is measured over them rather than the whole league.
        ahead = [r["entry"] for r in rows
                 if my_rank and r["rank"] < my_rank and r["entry"] in squads]

        counts = {}
        for eid in ahead:
            for pid in squads[eid]:
                counts[pid] = counts.get(pid, 0) + 1

        n = len(ahead)
        def share(pid):
            return (counts.get(pid, 0) / n) if n else 0.0

        differentials = sorted(
            [{"player_id": pid, "name": names.get(pid), "cost_m": costs.get(pid),
              "owned_by": counts.get(pid, 0), "share": round(share(pid), 3)}
             for pid in mine if share(pid) <= DIFFERENTIAL_THRESHOLD],
            key=lambda d: d["share"],
        )
        template_gaps = sorted(
            [{"player_id": pid, "name": names.get(pid), "cost_m": costs.get(pid),
              "owned_by": c, "share": round(share(pid), 3)}
             for pid, c in counts.items()
             if pid not in mine and share(pid) >= TEMPLATE_THRESHOLD],
            key=lambda d: -d["share"],
        )

        return {
            "league_id": league["id"],
            "league_name": league["name"],
            "league_size": league.get("rank_count"),
            "your_rank": my_rank,
            "rivals_ahead": n,
            "gameweek_read": last_played,
            "differentials": differentials,
            "template_gaps": template_gaps,
            "chips_spent": _chip_ledger(rows, entry_id),
        }
    except requests.RequestException as e:
        logger.warning("Rival view unavailable (%s) — continuing without it.", e)
        return None


def _chip_ledger(rows: list, entry_id: int) -> list:
    """Which chips everyone has already spent.

    A chip is a one-shot asset, so a rival who has burned their triple captain
    on an ordinary gameweek has permanently given up the 20-30 points it's
    worth on a double. That's a standing edge you hold over them, and it's
    invisible in the league table.
    """
    ledger = []
    for row in rows[:MAX_RIVALS]:
        try:
            history = _get(f"entry/{row['entry']}/history/")
        except requests.RequestException:
            continue
        ledger.append({
            "entry": row["entry"],
            "name": row["player_name"],
            "rank": row["rank"],
            "total": row["total"],
            "is_you": row["entry"] == entry_id,
            "chips": [{"chip": c["name"], "gameweek": c["event"]}
                      for c in history.get("chips", [])],
            "hits_cost": sum(e.get("event_transfers_cost", 0)
                             for e in history.get("current", [])),
        })
    return ledger
