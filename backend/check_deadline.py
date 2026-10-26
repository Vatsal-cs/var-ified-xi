"""
File: check_deadline.py
Path: var-ified-xi/backend/check_deadline.py

Decides whether the scheduled workflow should actually do any work.

The engine only needs to run in the day or so before an FPL deadline, but a
cron schedule fires regardless. This asks the FPL API when the next deadline
is and answers yes or no, so a scheduled run outside the window costs a few
seconds instead of several minutes of CI time.

It also says yes once right after a gameweek finishes, if the dashboard
hasn't been refreshed since: the new plan (and the Wildcard check) for next
week should be waiting the morning after the last match, not a day before the
next deadline. And once more when FPL marks that gameweek data_checked (bonus
points and autosubs added, usually some hours later), if the league table on
the dashboard was read before then: otherwise it shows provisional standings
until the next deadline window.

Writes `should_run` and `gameweek` to $GITHUB_OUTPUT for later workflow steps.
Run it locally too — it prints the same answer to stderr.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

from config import (BOOTSTRAP_URL, FIXTURES_URL, FRONTEND_JSON_PATH, REQUEST_HEADERS,
                    REQUEST_TIMEOUT)

# How long before a deadline the engine should start refreshing. Wide enough
# that a late or skipped cron run still lands inside it, and late enough that
# team news and price changes are mostly in.
WINDOW_HOURS = 30

# A match is over this long after kickoff (stoppage time, plus a margin).
MATCH_LENGTH = timedelta(hours=2)


def _finished_since_refresh(bootstrap: dict, now: datetime) -> bool:
    """True if the current gameweek's last match has ended and the dashboard
    was generated before it did."""
    current = next((e for e in bootstrap.get("events", []) if e.get("is_current")), None)
    if current is None:
        return False
    try:
        fixtures = requests.get(f"{FIXTURES_URL}?event={current['id']}", headers=REQUEST_HEADERS,
                                timeout=REQUEST_TIMEOUT).json()
    except requests.RequestException:
        return False
    kickoffs = [datetime.fromisoformat(f["kickoff_time"].replace("Z", "+00:00"))
                for f in fixtures if f.get("kickoff_time")]
    if not kickoffs or not all(f.get("finished_provisional") or f.get("finished") for f in fixtures):
        return False
    ended = max(kickoffs) + MATCH_LENGTH
    if now < ended:
        return False
    try:
        generated = datetime.fromisoformat(json.loads(FRONTEND_JSON_PATH.read_text())["generated_at"])
    except (OSError, KeyError, ValueError):
        return True
    return generated < ended


def _standings_confirmed_since_refresh(bootstrap: dict) -> bool:
    """True if FPL has confirmed the current gameweek's points and the
    dashboard's league table was read before it did."""
    current = next((e for e in bootstrap.get("events", []) if e.get("is_current")), None)
    if current is None or not current.get("data_checked"):
        return False
    try:
        league = json.loads(FRONTEND_JSON_PATH.read_text()).get("league")
    except (OSError, ValueError):
        return False
    if not league:
        return False
    return not (league.get("gameweek_read") == current["id"] and league.get("final"))


def main() -> int:
    force = os.environ.get("FORCE", "").lower() == "true"

    try:
        bootstrap = requests.get(
            BOOTSTRAP_URL, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT
        ).json()
    except requests.RequestException as e:
        # If FPL is unreachable we can't tell how close the deadline is.
        # Running anyway is the safer failure: main.py will surface the real
        # error, and a missed deadline is worse than a wasted CI minute.
        print(f"Could not reach the FPL API ({e}) — running anyway.", file=sys.stderr)
        _emit(True, "")
        return 0

    now = datetime.now(timezone.utc)
    upcoming = [
        (e["id"], datetime.fromisoformat(e["deadline_time"].replace("Z", "+00:00")))
        for e in bootstrap.get("events", [])
        if e.get("deadline_time")
    ]
    upcoming = [(gw, dt) for gw, dt in upcoming if dt > now]

    if not upcoming:
        print("No deadlines left this season.", file=sys.stderr)
        _emit(force, "")
        return 0

    gameweek, deadline = min(upcoming, key=lambda pair: pair[1])
    hours = (deadline - now).total_seconds() / 3600

    after_gameweek = (not force and hours > WINDOW_HOURS
                      and _finished_since_refresh(bootstrap, now))
    confirmed = (not force and hours > WINDOW_HOURS and not after_gameweek
                 and _standings_confirmed_since_refresh(bootstrap))
    should_run = force or hours <= WINDOW_HOURS or after_gameweek or confirmed
    reason = (" — a gameweek just finished" if after_gameweek
              else " — FPL confirmed the gameweek's points" if confirmed else "")
    print(
        f"GW{gameweek} deadline in {hours:.1f}h "
        f"({'running' if should_run else 'skipping'}{reason}).",
        file=sys.stderr,
    )
    _emit(should_run, gameweek)
    return 0


def _emit(should_run: bool, gameweek) -> None:
    line = f"should_run={str(bool(should_run)).lower()}\ngameweek={gameweek}\n"
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a") as fh:
            fh.write(line)
    else:
        print(line, end="")


if __name__ == "__main__":
    sys.exit(main())
