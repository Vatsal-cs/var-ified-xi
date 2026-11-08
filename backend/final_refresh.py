"""
File: final_refresh.py
Path: var-ified-xi/backend/final_refresh.py

Makes sure the last plan before each deadline has read the day's team news.

The refresh asks for a run every four hours, but GitHub has been running it
about three times a day: before GW10 2026-27 the last run was 5.5 hours before
the deadline, and the next would have come two hours after it, so that
morning's press conferences would never have been read. This job
(.github/workflows/final-refresh.yml) waits until TEAM_NEWS_FINAL_READ_HOURS
before the deadline and starts a refresh then, unless the news has already been
read since. team_news.get() won't reuse an older read inside that window, and
deadline_reminder.py sends its second email once that read is in. A deadline
before REMINDER_EARLY_HOUR gets one more, just before the evening reminder
(config.news_read_marks).

    python final_refresh.py --wait    # sleeps until the window, if it opens soon
    python final_refresh.py           # writes should_refresh to $GITHUB_OUTPUT
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

from config import FRONTEND_JSON_PATH, news_read_marks
from deadline_reminder import _span, last_read, next_deadline, time_to_wait

# A refresh takes minutes and the site redeploys after it. Later than this, it
# would land too close to the deadline to act on.
TOO_LATE = timedelta(minutes=20)


def should_refresh(deadline: datetime, now: datetime, last_read: datetime | None) -> bool:
    """Has a read mark passed with no read since it?"""
    passed = [m for m in news_read_marks(deadline) if m <= now]
    if not passed or deadline - now < TOO_LATE:
        return False
    return last_read is None or last_read < passed[-1]


def _emit(refresh: bool) -> None:
    line = f"should_refresh={str(refresh).lower()}\n"
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a") as fh:
            fh.write(line)
    else:
        print(line, end="")


def main(argv: list | None = None) -> int:
    wait = "--wait" in (sys.argv[1:] if argv is None else argv)
    now = datetime.now(timezone.utc)
    found = next_deadline(json.loads(FRONTEND_JSON_PATH.read_text()), now)
    if found is None:
        if not wait:
            _emit(False)
        return 0
    gameweek, deadline = found
    if wait:
        mark = next((m for m in news_read_marks(deadline) if m > now), None)
        pause = time_to_wait(mark, now) if mark else None
        if pause:
            print(f"GW{gameweek}: waiting {_span(pause)} for the next news read.", file=sys.stderr)
            time.sleep(pause.total_seconds())
        return 0
    refresh = should_refresh(deadline, now, last_read())
    print(f"GW{gameweek} deadline in {_span(deadline - now)}: "
          f"{'starting the final refresh' if refresh else 'no refresh needed'}.", file=sys.stderr)
    _emit(refresh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
