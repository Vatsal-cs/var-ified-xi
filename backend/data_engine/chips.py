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


def _best_triple_captain(predictions_df, gw: int, owned_squad: list = None):
    """The single best Triple Captain target for a specific gameweek.

    Restricted to your owned squad when one is given (the real question —
    "should I TC someone I actually have"); otherwise scans the whole pool,
    which is what matters BEFORE the gameweek is close enough to plan transfers
    around, so you know who to start buying toward.
    """
    if predictions_df is None or "xp_by_gw" not in predictions_df.columns:
        return None

    pool = predictions_df
    if owned_squad is not None:
        pool = pool[pool["player_id"].isin(owned_squad)]
    if pool.empty:
        return None

    combined = pool["xp_by_gw"].apply(lambda d: float((d or {}).get(gw, 0.0)))
    if combined.max() <= 0:
        return None
    best = pool.loc[combined.idxmax()]
    return {
        "player_id": int(best["player_id"]),
        "name": best.get("web_name"),
        "combined_points": round(float(combined.max()), 1),
        "owned": owned_squad is not None,
    }


def _bench_boost_value(predictions_df, gw: int, bench_ids: list):
    """Combined projected points your CURRENT bench would add if boosted."""
    if predictions_df is None or "xp_by_gw" not in predictions_df.columns or not bench_ids:
        return None
    pool = predictions_df[predictions_df["player_id"].isin(bench_ids)]
    if pool.empty:
        return None
    total = pool["xp_by_gw"].apply(lambda d: float((d or {}).get(gw, 0.0))).sum()
    return round(float(total), 1)


def advise(fixtures: list, teams: list, horizon_start: int,
           chips_available: list = None, horizon: int = HORIZON_GWS,
           predictions_df=None, owned_squad: list = None, bench_ids: list = None) -> list:
    """Turns the fixture calendar into chip suggestions.

    Only suggests chips you still hold. When predictions_df is given and the
    gameweek falls inside the planning horizon, the advice names an actual
    player and a projected number instead of just "this looks like the week"
    — e.g. "Triple Captain Haaland — projected 19.4 combined points" rather
    than a generic reminder. Outside the horizon (which is normal — doubles
    are usually only confirmed a few weeks out) it stays generic, since
    there's no honest way to say who you'd own that far ahead.

    Returns a list of {chip, gameweek, reason} in the order they'd be used.
    """
    available = set(chips_available if chips_available is not None
                    else ["wildcard", "bboost", "3xc", "freehit"])
    special = find_special_gameweeks(fixtures, teams, horizon_start, horizon)
    advice = []

    for double in special["doubles"]:
        gw, n = double["gameweek"], len(double["teams"])
        if "bboost" in available:
            bb_value = _bench_boost_value(predictions_df, gw, bench_ids)
            reason = (
                f"Your current bench projects {bb_value} combined points in GW{gw} "
                f"if boosted — {n} teams play twice."
                if bb_value is not None else
                f"{n} teams play twice in GW{gw} — all 15 of your players "
                f"score, so a bench of doublers is worth far more than usual."
            )
            advice.append({"chip": "bboost", "gameweek": gw, "reason": reason})
        if "3xc" in available:
            tc = _best_triple_captain(predictions_df, gw, owned_squad)
            if tc:
                who = "your" if tc["owned"] else "the league's"
                reason = (
                    f"Triple Captain {tc['name']} — {who} best target, projected "
                    f"{tc['combined_points']} combined points across GW{gw}'s two fixtures."
                )
            else:
                reason = (
                    "A triple captain on a double gameweek gets three times the "
                    "points from two matches instead of one."
                )
            advice.append({"chip": "3xc", "gameweek": gw, "reason": reason})

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
            logger.info("Chip suggestion: %s in GW%d — %s",
                       item["chip"], item["gameweek"], item["reason"])
    return advice


def scan_full_season(fixtures: list, teams: list, last_finished_gw: int = 0) -> dict:
    """A season-wide, non-actionable check: is there ANY double or blank
    gameweek anywhere on the currently published calendar, regardless of
    whether it's close enough to act on yet?

    This exists purely to answer "are you actually watching for this" —
    doubles are usually only confirmed a few gameweeks in advance (they come
    from cup-replay and European-fixture reschedules), so most of a season
    this correctly finds nothing. Finding nothing is not the same as the
    tool being silent about it: see the caller for how the empty case is
    surfaced.
    """
    upcoming = max(1, last_finished_gw + 1)
    return find_special_gameweeks(fixtures, teams, upcoming, horizon=38 - upcoming + 1)
