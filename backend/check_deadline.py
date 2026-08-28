"""
File: check_deadline.py
Path: var-ified-xi/backend/check_deadline.py

Decides whether the scheduled workflow should actually do any work.

The engine only needs to run in the day or so before an FPL deadline, but a
cron schedule fires regardless. This asks the FPL API when the next deadline
is and answers yes or no, so a scheduled run outside the window costs a few
seconds instead of several minutes of CI time.

Writes `should_run` and `gameweek` to $GITHUB_OUTPUT for later workflow steps.
Run it locally too — it prints the same answer to stderr.
"""

import os
import sys
from datetime import datetime, timezone

import requests

from config import BOOTSTRAP_URL, REQUEST_HEADERS, REQUEST_TIMEOUT

# How long before a deadline the engine should start refreshing. Wide enough
# that a late or skipped cron run still lands inside it, and late enough that
# team news and price changes are mostly in.
WINDOW_HOURS = 30


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

    should_run = force or hours <= WINDOW_HOURS
    print(
        f"GW{gameweek} deadline in {hours:.1f}h "
        f"({'running' if should_run else 'skipping'}).",
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
