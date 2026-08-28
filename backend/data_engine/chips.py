"""
File: chips.py
Path: var-ified-xi/backend/data_engine/chips.py

Spots the gameweeks worth spending a chip on.

Chips are the biggest single-week swings available in FPL — a bench boost on a
double gameweek is worth far more than any transfer — and the whole game is
knowing which week to use them. That decision hinges almost entirely on the
fixture calendar rather than on the model: which gameweeks have teams playing
twice (doubles), and which have teams not playing at all (blanks).

Both are visible in the fixture list well in advance, so this reads them
straight from the data already fetched and turns them into plain advice. It
deliberately stops at "this looks like the week" — chip timing depends on your
rivals and your own squad in ways a solver shouldn't pretend to settle.
"""

import logging
from collections import Counter, defaultdict

from config import HORIZON_GWS

logger = logging.getLogger(__name__)

# A gameweek is only worth flagging if a meaningful number of teams are
# affected. One rescheduled match is noise; six teams playing twice is a chip.
DOUBLE_TEAM_THRESHOLD = 4
BLANK_TEAM_THRESHOLD = 4


def fixture_counts_by_gameweek(fixtures: list, horizon_start: int, horizon: int) -> dict:
    """{gameweek: {team_id: number of fixtures}} across the horizon."""
    counts = defaultdict(Counter)
    for fixture in fixtures:
        gw = fixture.get("event")
        if gw is None or not (horizon_start <= gw < horizon_start + horizon):
            continue
        counts[gw][fixture["team_h"]] += 1
        counts[gw][fixture["team_a"]] += 1
    return counts


def find_special_gameweeks(fixtures: list, teams: list, horizon_start: int,
                           horizon: int = HORIZON_GWS) -> dict:
    """Identifies double and blank gameweeks in the horizon."""
    all_teams = {t["id"] for t in teams}
    counts = fixture_counts_by_gameweek(fixtures, horizon_start, horizon)

    doubles, blanks = [], []
    for gw in sorted(counts):
        playing = counts[gw]
        doubled = [t for t, n in playing.items() if n >= 2]
        missing = [t for t in all_teams if playing.get(t, 0) == 0]

        if len(doubled) >= DOUBLE_TEAM_THRESHOLD:
            doubles.append({"gameweek": gw, "teams": sorted(doubled)})
        if len(missing) >= BLANK_TEAM_THRESHOLD:
            blanks.append({"gameweek": gw, "teams": sorted(missing)})

    return {"doubles": doubles, "blanks": blanks}


def advise(fixtures: list, teams: list, horizon_start: int,
           chips_available: list = None, horizon: int = HORIZON_GWS) -> list:
    """Turns the fixture calendar into chip suggestions.

    Only suggests chips you still hold. Returns a list of
    {chip, gameweek, reason} in the order they'd be used.
    """
    available = set(chips_available if chips_available is not None
                    else ["wildcard", "bboost", "3xc", "freehit"])
    special = find_special_gameweeks(fixtures, teams, horizon_start, horizon)
    advice = []

    for double in special["doubles"]:
        gw, n = double["gameweek"], len(double["teams"])
        if "bboost" in available:
            advice.append({
                "chip": "bboost",
                "gameweek": gw,
                "reason": f"{n} teams play twice in GW{gw} — all 15 of your players "
                          f"score, so a bench of doublers is worth far more than usual.",
            })
        if "3xc" in available:
            advice.append({
                "chip": "3xc",
                "gameweek": gw,
                "reason": f"A triple captain on a double gameweek gets three times the "
                          f"points from two matches instead of one.",
            })

    for blank in special["blanks"]:
        gw, n = blank["gameweek"], len(blank["teams"])
        if "freehit" in available:
            advice.append({
                "chip": "freehit",
                "gameweek": gw,
                "reason": f"{n} teams have no fixture in GW{gw}. A free hit fields a "
                          f"one-week squad of only the teams that are playing, then "
                          f"reverts — no lasting damage to your squad.",
            })
        elif "wildcard" in available:
            advice.append({
                "chip": "wildcard",
                "gameweek": gw,
                "reason": f"{n} teams blank in GW{gw}. Without a free hit, a wildcard "
                          f"is the way to field a full eleven.",
            })

    if advice:
        for item in advice:
            logger.info("Chip suggestion: %s in GW%d", item["chip"], item["gameweek"])
    return advice
