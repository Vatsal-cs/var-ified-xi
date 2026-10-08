"""
File: rules.py
Path: var-ified-xi/backend/data_engine/rules.py

The transfer economy each FPL season was actually played under.

The live pipeline only ever needs this season's rules, and reads the bank cap
from config (cross-checked against the API by entry_data). Replaying a PAST
season is different: the harnesses have to give the simulated manager the
transfers a real manager had that year, or every policy they compare is
measured against a game nobody played. The season simulator used to apply
today's cap to every season; for 2022-23 and 2023-24 that hands out three
free transfers a week that didn't exist.

What changed, season by season (official FPL announcements):

    2022-23  bank up to 2. Unlimited free transfers between the GW16 and
             GW17 deadlines, for the World Cup break.
    2023-24  bank up to 2.
    2024-25  bank up to 5 (new that season).
    2025-26  bank up to 5, and every manager topped up to 5 for GW16, ahead
             of the Africa Cup of Nations.
    2026-27  bank up to 5.

Two things are inferred rather than documented, and say so where they're
used: a team's first gameweek banks nothing (fits the user's own history,
guarded by tests/test_rules.py), and after the 2022-23 unlimited week the bank
restarts from one, as it did after a Wildcard under that season's rules.

Chips aren't here. Neither harness plays them, so a chip table would be code
with no caller.
"""

from dataclasses import dataclass, field

import config

# Enough free transfers to replace the whole squad, which is what "unlimited"
# means in practice.
UNLIMITED = config.SQUAD_SIZE


@dataclass(frozen=True)
class SeasonRules:
    max_free_transfers: int
    # {gameweek: n} — before that gameweek's deadline every manager's bank is
    # raised to at least n.
    topups: dict = field(default_factory=dict)
    # Gameweeks whose transfers were all free.
    unlimited_gws: tuple = ()


SEASON_RULES = {
    "2022-23": SeasonRules(max_free_transfers=2, unlimited_gws=(17,)),
    "2023-24": SeasonRules(max_free_transfers=2),
    "2024-25": SeasonRules(max_free_transfers=5),
    "2025-26": SeasonRules(max_free_transfers=5, topups={16: 5}),
    "2026-27": SeasonRules(max_free_transfers=5),
}


def for_season(season: str) -> SeasonRules:
    """The rules for `season`. An unknown season gets today's, loudly."""
    if season in SEASON_RULES:
        return SEASON_RULES[season]
    import logging
    logging.getLogger(__name__).warning(
        "No transfer rules recorded for %s; using today's (bank up to %d).",
        season, config.MAX_FREE_TRANSFERS)
    return SeasonRules(max_free_transfers=config.MAX_FREE_TRANSFERS)


def free_transfers_for(rules: SeasonRules, gameweek: int, banked: int) -> int:
    """Free transfers available at `gameweek`'s deadline, given what the
    normal accrual left in the bank. Applies that week's top-up, or the whole
    squad's worth if the week was unlimited."""
    if gameweek in rules.unlimited_gws:
        return UNLIMITED
    return max(banked, rules.topups.get(gameweek, 0))


def bank_after(rules: SeasonRules, gameweek: int, available: int, used: int) -> int:
    """What carries into the NEXT gameweek: unused transfers plus the one
    earned, capped. An unlimited week banks nothing of its own."""
    if gameweek in rules.unlimited_gws:
        return 1
    return min(max(available - used, 0) + 1, rules.max_free_transfers)
