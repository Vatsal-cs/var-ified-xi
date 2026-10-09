"""
File: horizon_availability.py
Path: var-ified-xi/backend/data_engine/horizon_availability.py

How available a flagged player is in the weeks AFTER next.

FPL's flags are about the next gameweek. Production keeps a hard flag
(injured, suspended) on every week of the six-week horizon at a tenth of the
player's projection, which is right for a player who has left the club and
badly wrong for most others. Measured on regular starters (5-game minutes
average 60+) before each 2024-25 and 2025-26 deadline, relative to an
unflagged regular's chance of playing the same week:

                       next   +1     +2     +3     +4     +5
    suspended          0.05   0.82   0.90   1.0    1.0    1.0
    injured, no date   0.07   0.24   0.42   0.52   0.64   0.69
    production today   0.10   0.10   0.10   0.10   0.10   0.10

Both seasons give the same curves to within a few points. FPL's news text
often says more:

    "Suspended until 02 Nov"   72% return in exactly that gameweek
    "Expected back 13 Dec"     0-20% play before it, ~73% that week, ~85% after

This module rewrites the flags on the LATER horizon rows to say that. The
next gameweek is untouched — FPL's own chance_of_playing already describes
it. A player who left the club ('u') or isn't registered ('n') stays out, and
a doubt ('d') already only counts for the next week
(feature_engineering.limit_flags_to_next_round).

It works by setting status to available and chance_of_playing to the factor,
so train_model.predict_points applies it exactly as it applies FPL's own
percentage, and a week where the player is still out keeps the hard flag.

The factors are rounded from the table above, so they were read off the same
two seasons the harness tests on. They are the same in both seasons, and the
rule has no knob tuned against points, but the live season is the only
holdout that never informed them.

Off in production until it passes its test (config.HORIZON_AVAILABILITY).
"""

import re

import pandas as pd

# Relative availability, by gameweeks after the next one, for an injured
# player with no return date.
INJURY_UNDATED = {1: 0.25, 2: 0.40, 3: 0.50, 4: 0.60, 5: 0.65}

# Injured with a return date: well before it he's out; in the last fortnight
# before it some come back early; from it on most are back.
INJURY_DATED_SOON = 0.20
INJURY_DATED_BACK = 0.80
SOON_DAYS = 14

# Suspended, once the ban is served.
SUSPENSION_SERVED = 0.90

_DATE = re.compile(r"(Expected back|Suspended until) (\d{1,2}) ([A-Za-z]{3})")


def parse_return(news, reference: pd.Timestamp):
    """("expected" | "suspended", date) from FPL's news text, or (None, None).

    The text gives day and month only, so the year is whichever puts the date
    nearest after the reference (the deadline): "05 Jan" read in December is
    next January.
    """
    if not isinstance(news, str) or reference is None or pd.isna(reference):
        return None, None
    m = _DATE.search(news)
    if not m:
        return None, None
    kind = "suspended" if m.group(1).startswith("Suspended") else "expected"
    try:
        date = pd.Timestamp(f"{m.group(2)} {m.group(3)} {reference.year}")
    except ValueError:
        return None, None
    if date < reference.normalize() - pd.Timedelta(days=60):
        date = date.replace(year=reference.year + 1)
    return kind, date


def factor(status: str, kind, return_date, weeks_ahead: int, kickoff) -> float:
    """Availability for one horizon row, or None to keep the hard flag.

    weeks_ahead counts gameweeks after the next one (1 = the week after).
    kickoff is that fixture's kickoff, used against a stated return date.
    """
    if weeks_ahead < 1:
        return None
    if status == "s":
        if kind == "suspended" and kickoff is not None and pd.notna(kickoff) \
                and kickoff.normalize() < return_date:
            return None                       # ban not yet served
        return SUSPENSION_SERVED
    if status == "i":
        if kind == "expected" and kickoff is not None and pd.notna(kickoff):
            days = (return_date - kickoff.normalize()).days
            if days > SOON_DAYS:
                return None                   # still well short of the date
            if days > 0:
                return INJURY_DATED_SOON
            return INJURY_DATED_BACK
        return INJURY_UNDATED.get(weeks_ahead, max(INJURY_UNDATED.values()))
    return None


def apply(rows: pd.DataFrame, first_gw, deadline: pd.Timestamp,
          gw_col: str = "gw", kickoff_col: str = "fixture_kickoff") -> None:
    """Rewrites flags on horizon rows after `first_gw`, in place.

    Needs `status` and `news` (news may be empty) and, for dated returns,
    each row's fixture kickoff in `kickoff_col`. Rows for the next gameweek
    are never touched.
    """
    if rows.empty or first_gw is None or "status" not in rows.columns:
        return
    later = (rows[gw_col] > first_gw) & rows["status"].isin(["i", "s"])
    if not later.any():
        return
    if "chance_of_playing" not in rows.columns:
        rows["chance_of_playing"] = None
    news = rows["news"] if "news" in rows.columns else pd.Series("", index=rows.index)
    kickoffs = rows[kickoff_col] if kickoff_col in rows.columns else pd.Series(None, index=rows.index)

    parsed = {}
    for idx in rows.index[later]:
        text = news.get(idx, "")
        if text not in parsed:
            parsed[text] = parse_return(text, deadline)
        kind, date = parsed[text]
        f = factor(rows.at[idx, "status"], kind, date,
                   int(rows.at[idx, gw_col] - first_gw), kickoffs.get(idx))
        if f is not None:
            rows.at[idx, "status"] = "a"
            rows.at[idx, "chance_of_playing"] = round(f * 100, 1)
