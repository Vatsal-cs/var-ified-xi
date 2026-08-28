"""
File: entry_data.py
Path: var-ified-xi/backend/data_engine/entry_data.py

Reads YOUR actual FPL team from the public entry endpoints — no login, no
password, no session cookie. Everything here is data FPL already serves to
anyone who has your team id, which is the number in your team's public URL:

    https://fantasy.premierleague.com/entry/1234567/event/2
                                            ^^^^^^^

Why this matters: an optimizer that rebuilds a £100m squad from scratch every
week is answering a question nobody can act on. After gameweek 1 you don't get
15 free picks — you get one free transfer a week (bankable to five), and a -4
point hit for each extra. The only useful advice is "given the team you
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


def _free_transfers(entry_id: int, upcoming_gw: int) -> int:
    """Reconstructs how many free transfers you'll have.

    FPL doesn't publish this directly, so it's rebuilt from the rule: you gain
    one per gameweek, you can bank up to MAX_FREE_TRANSFERS, and each transfer
    you make spends one. Wildcard and free-hit weeks don't consume them.
    """
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

    free = 1
    for event in sorted(history.get("current", []), key=lambda e: e["event"]):
        gw = event["event"]
        if gw >= upcoming_gw:
            break
        if gw not in chip_weeks:
            free -= event.get("event_transfers", 0)
            free = max(free, 0)
        free = min(free + 1, MAX_FREE_TRANSFERS)

    return max(1, min(free, MAX_FREE_TRANSFERS))


ALL_CHIPS = ["wildcard", "bboost", "3xc", "freehit"]


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
        used = [c["name"] for c in fetch_entry_history(entry_id).get("chips", [])]
    except requests.RequestException:
        used = []

    state = TeamState(
        entry_id=entry_id,
        name=entry.get("name", f"Entry {entry_id}"),
        gameweek=upcoming_gw,
        squad=squad,
        bank=bank,
        squad_value=value,
        free_transfers=_free_transfers(entry_id, upcoming_gw),
        sell_prices=sell_prices,
        chips_used=used,
        # Each chip is available once per season. (FPL's second-half chip
        # reset isn't modelled — the planner only ever looks a few weeks out.)
        chips_available=[c for c in ALL_CHIPS if c not in used],
    )

    logger.info(
        "Team '%s' (id %d): %d players, £%.1fm in the bank, %d free transfer(s), "
        "chips left: %s",
        state.name, entry_id, len(squad), bank / 10, state.free_transfers,
        ", ".join(state.chips_available) or "none",
    )
    return state
