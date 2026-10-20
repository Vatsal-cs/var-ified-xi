"""
File: entry_data.py
Path: var-ified-xi/backend/data_engine/entry_data.py

Reads YOUR actual FPL team from the public entry endpoints — no login, no
password, no session cookie. Everything here is data FPL already serves to
anyone who has your team id, which is the number in your team's public URL:

    https://fantasy.premierleague.com/entry/1234567/event/2
                                            ^^^^^^^

Why this matters: an optimizer that rebuilds a £100m squad from scratch every
week is answering a question nobody can act on. After your first gameweek you
don't get 15 free picks — you get one free transfer a week (bankable to five),
and a -4 point hit for each extra. The only useful advice is "given the team you
actually own, what should change", and that starts here.

Endpoints used (all public):
    entry/{id}/                    name, bank, squad value, current gameweek
    entry/{id}/event/{gw}/picks/   the 15 players you own right now
    entry/{id}/transfers/          every transfer you've made, with prices
    entry/{id}/history/            chips already used
"""

import logging
from dataclasses import dataclass, field

import requests

from config import (
    FPL_BASE_URL,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
    MAX_FREE_TRANSFERS,
)

logger = logging.getLogger(__name__)


@dataclass
class TeamState:
    """Everything the transfer planner needs to know about your team."""
    entry_id: int
    name: str
    gameweek: int                      # the gameweek being planned FOR
    squad: list                        # player_ids you currently own
    bank: int                          # tenths of a million, e.g. 12 = £1.2m
    squad_value: int                   # tenths of a million
    free_transfers: int
    sell_prices: dict = field(default_factory=dict)   # player_id -> tenths
    chips_used: list = field(default_factory=list)
    chips_available: list = field(default_factory=list)
    # {chip name: last gameweek it can be played}. Chips come in two
    # half-season sets, and an unused first-half chip is simply lost.
    chip_deadlines: dict = field(default_factory=dict)

    @property
    def budget(self) -> int:
        """Total spending power if the whole squad were sold."""
        return self.bank + sum(self.sell_prices.get(p, 0) for p in self.squad)


def _get(path: str):
    url = f"{FPL_BASE_URL}/{path}"
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_entry(entry_id: int) -> dict:
    return _get(f"entry/{entry_id}/")


def fetch_picks(entry_id: int, gameweek: int) -> dict:
    return _get(f"entry/{entry_id}/event/{gameweek}/picks/")


def fetch_transfers(entry_id: int) -> list:
    return _get(f"entry/{entry_id}/transfers/")


def fetch_entry_history(entry_id: int) -> dict:
    return _get(f"entry/{entry_id}/history/")


def compute_sell_price(purchase_price: int, current_price: int) -> int:
    """FPL's selling rule: you keep only half of any rise, rounded down.

    Prices are in tenths of a million throughout, so "half the profit, rounded
    down to the nearest £0.1m" is exactly integer division by two. A player who
    has fallen in price sells for what he is worth now, with no cushion.
    """
    if current_price <= purchase_price:
        return current_price
    return purchase_price + (current_price - purchase_price) // 2


def _purchase_prices(entry_id: int, squad: list, player_histories: dict,
                     bootstrap: dict) -> dict:
    """What you actually paid for each player you own.

    The transfers endpoint records the price of every player bought. Anyone
    still in the squad from your initial draft was never "bought", so their
    purchase price is their price in the first gameweek — which the
    element-summary history already gives us.
    """
    prices = {}

    try:
        transfers = fetch_transfers(entry_id)
    except requests.RequestException as e:
        logger.warning("Could not read transfer history (%s) — assuming no "
                       "price changes since purchase.", e)
        transfers = []

    # Transfers come back newest-first; walking in reverse leaves the most
    # recent purchase price for a player who was bought more than once.
    for t in reversed(transfers):
        prices[t["element_in"]] = t["element_in_cost"]

    meta = {p["id"]: p for p in bootstrap["elements"]}
    for pid in squad:
        if pid in prices:
            continue
        history = (player_histories.get(pid) or {}).get("history") or []
        if history:
            prices[pid] = history[0].get("value", meta.get(pid, {}).get("now_cost", 0))
        else:
            # Never appeared this season — the best available estimate is
            # today's price, which makes their sell price a no-op.
            prices[pid] = meta.get(pid, {}).get("now_cost", 0)

    return prices


def replay_free_transfers(events: list, chip_weeks: set, upcoming_gw: int,
                          cap: int = MAX_FREE_TRANSFERS) -> int:
    """Free transfers available for `upcoming_gw`, rebuilt from history.

    FPL doesn't publish this, so it's replayed from the rules:

      * A team's first gameweek is a free squad pick. It banks nothing, so
        the week after it starts with exactly one free transfer — whether the
        team was created before GW1 or joined later in the season.
      * Every later gameweek adds one, up to `cap`.
      * Transfers spend them. A Wildcard or Free Hit week spends none, and
        adds none either: the next week starts with what that week had.
        (FPL keeps the transfers you'd SAVED; that week's own one is used by
        the chip. Checked against the app, GW8 2026-27: one free transfer
        into the Wildcard week, one after it, not two.)

    events: entry history rows ({"event", "event_transfers"}), any order.
    """
    played = sorted((e for e in events if e["event"] < upcoming_gw),
                    key=lambda e: e["event"])
    if not played:
        return 1

    free = 0                      # the creation week banks nothing
    for e in played:
        if e["event"] in chip_weeks:
            continue
        free = max(free - e.get("event_transfers", 0), 0)
        free = min(free + 1, cap)
    return max(1, free)


def _free_transfers(entry_id: int, upcoming_gw: int, cap: int = MAX_FREE_TRANSFERS) -> int:
    """Free transfers for the coming gameweek, from your public history."""
    try:
        history = fetch_entry_history(entry_id)
    except requests.RequestException as e:
        logger.warning("Could not read entry history (%s) — assuming 1 free "
                       "transfer.", e)
        return 1

    chip_weeks = {
        c["event"] for c in history.get("chips", [])
        if c.get("name") in ("wildcard", "freehit")
    }
    return replay_free_transfers(history.get("current", []), chip_weeks, upcoming_gw, cap)


def free_transfer_cap(bootstrap: dict) -> int:
    """The banking cap FPL is actually running, cross-checked against config.

    The live API states it as max_extra_free_transfers (banked on top of the
    weekly one). The config value is what the optimizer is built against, so a
    mismatch is logged loudly rather than silently followed.
    """
    extra = (bootstrap.get("game_settings") or {}).get("max_extra_free_transfers")
    if extra is None:
        return MAX_FREE_TRANSFERS
    live = 1 + int(extra)
    if live != MAX_FREE_TRANSFERS:
        logger.warning(
            "FPL now allows %d free transfers but config.MAX_FREE_TRANSFERS is "
            "%d. Update config — the planner is using the wrong transfer economy.",
            live, MAX_FREE_TRANSFERS)
    return live


ALL_CHIPS = ["wildcard", "bboost", "3xc", "freehit"]


def available_chips(bootstrap: dict, chips_used: list, gameweek: int) -> dict:
    """Chips you can still play in `gameweek`, with the last week each can be.

    FPL issues chips per window — since 2025/26, one full set for GW1-19 and a
    second for GW20-38 — and bootstrap-static lists every window's
    start_event and stop_event. A chip is available if its window contains this
    gameweek and you haven't played that chip inside that window. A first-half
    chip left unplayed at the GW19 deadline is gone; it does not roll over.

    chips_used: entry history chip rows ({"name", "event"}).
    Returns {chip name: stop_event}.
    """
    windows = bootstrap.get("chips") or []
    if not windows:
        # Older payloads without chip windows: one set for the whole season.
        spent = {c["name"] for c in chips_used}
        return {name: 38 for name in ALL_CHIPS if name not in spent}

    out = {}
    for w in windows:
        if not (w["start_event"] <= gameweek <= w["stop_event"]):
            continue
        spent = any(c["name"] == w["name"] and w["start_event"] <= c["event"] <= w["stop_event"]
                    for c in chips_used)
        if not spent:
            out[w["name"]] = w["stop_event"]
    return out


def build_team_state(entry_id: int, bootstrap: dict, player_histories: dict,
                     upcoming_gw: int) -> TeamState:
    """Assembles the full picture of your team as it stands right now."""
    entry = fetch_entry(entry_id)

    # Picks are published for finished gameweeks, so we read the last one
    # played to learn which 15 players you currently hold.
    last_played = upcoming_gw - 1
    if last_played < 1:
        raise ValueError(
            "There is no completed gameweek yet, so FPL has not published a "
            "squad for this team. The fresh-squad optimizer is the right tool "
            "before gameweek 1."
        )

    picks = fetch_picks(entry_id, last_played)
    squad = [p["element"] for p in picks["picks"]]

    entry_history = picks.get("entry_history", {})
    bank = entry_history.get("bank", entry.get("last_deadline_bank") or 0)
    value = entry_history.get("value", entry.get("last_deadline_value") or 0)

    purchase = _purchase_prices(entry_id, squad, player_histories, bootstrap)
    meta = {p["id"]: p for p in bootstrap["elements"]}
    sell_prices = {
        pid: compute_sell_price(purchase.get(pid, 0),
                                meta.get(pid, {}).get("now_cost", 0))
        for pid in squad
    }

    try:
        chip_rows = fetch_entry_history(entry_id).get("chips", [])
    except requests.RequestException:
        chip_rows = []
    deadlines = available_chips(bootstrap, chip_rows, upcoming_gw)

    state = TeamState(
        entry_id=entry_id,
        name=entry.get("name", f"Entry {entry_id}"),
        gameweek=upcoming_gw,
        squad=squad,
        bank=bank,
        squad_value=value,
        free_transfers=_free_transfers(entry_id, upcoming_gw, free_transfer_cap(bootstrap)),
        sell_prices=sell_prices,
        chips_used=[c["name"] for c in chip_rows],
        chips_available=[c for c in ALL_CHIPS if c in deadlines],
        chip_deadlines=deadlines,
    )

    logger.info(
        "Team '%s' (id %d): %d players, £%.1fm in the bank, %d free transfer(s), "
        "chips left: %s",
        state.name, entry_id, len(squad), bank / 10, state.free_transfers,
        ", ".join(f"{c} (by GW{deadlines[c]})" for c in state.chips_available) or "none",
    )
    return state
