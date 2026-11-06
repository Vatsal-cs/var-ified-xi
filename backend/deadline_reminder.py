"""
File: deadline_reminder.py
Path: var-ified-xi/backend/deadline_reminder.py

Tells you what to do before each FPL deadline, without opening the site.

Runs on GitHub Actions (.github/workflows/deadline-reminder.yml). The first run
inside the last REMINDER_HOURS before a deadline posts the week's plan as a
comment on one GitHub issue, mentioning the repo's owner. GitHub turns the
mention into an email and a push on its mobile app, so this needs no mail
account, no key and no money: the workflow's own token is enough.

The schedule asks for hourly, but GitHub's scheduler doesn't keep to that: in
the first days the job ran every 5-8 hours. So a run that lands in the hours
before the window waits for it (--wait), and then reads the newest plan.

One reminder per gameweek, however many runs land in the window. The comments
already on the issue are the record of that, so there's no state to commit.

    python deadline_reminder.py --preview    # prints the message, sends nothing
    python deadline_reminder.py --wait       # sleeps until the window, if it opens soon
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from config import (BOOTSTRAP_URL, FRONTEND_JSON_PATH, REMINDER_HOURS, REMINDER_ISSUE_TITLE,
                    REMINDER_MAX_WAIT_HOURS, REMINDER_UTC_OFFSET, REQUEST_HEADERS, REQUEST_TIMEOUT,
                    SITE_URL)

GITHUB_API = "https://api.github.com"
CHIP_NAMES = {"bboost": "Bench Boost", "3xc": "Triple Captain", "freehit": "Free Hit",
              "wildcard": "Wildcard"}
NEWS_WORDS = {"out": "out", "doubtful": "doubtful", "rotation_risk": "could be benched"}
# The refresh runs every four hours and can run hours late; past this it's stuck.
STALE_AFTER = timedelta(hours=10)


def _utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def next_deadline(plan: dict, now: datetime) -> tuple | None:
    """(gameweek, deadline) from FPL, or from the plan if FPL can't be reached:
    an hourly check shouldn't lose the reminder to one failed request."""
    try:
        events = requests.get(BOOTSTRAP_URL, headers=REQUEST_HEADERS,
                              timeout=REQUEST_TIMEOUT).json()["events"]
        dates = [(_utc(e["deadline_time"]), e["id"]) for e in events if e.get("deadline_time")]
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Could not read FPL's deadlines ({e}) — using the plan's.", file=sys.stderr)
        dates = [(_utc(plan["deadline"]), plan["gameweek"])] if plan.get("deadline") else []
    upcoming = [d for d in dates if d[0] > now]
    if not upcoming:
        return None
    deadline, gameweek = min(upcoming)
    return gameweek, deadline


def is_due(deadline: datetime, now: datetime) -> bool:
    return deadline - now <= timedelta(hours=REMINDER_HOURS)


def time_to_wait(deadline: datetime, now: datetime, hours: float = REMINDER_HOURS) -> timedelta | None:
    """How long until the window opens, if a run should wait that long."""
    wait = deadline - now - timedelta(hours=hours)
    return wait if timedelta(0) < wait <= timedelta(hours=REMINDER_MAX_WAIT_HOURS) else None


def _clock(deadline: datetime) -> str:
    d = deadline.astimezone(timezone(timedelta(hours=REMINDER_UTC_OFFSET)))
    return f"{d:%a} {d.day} {d:%b}, {d.hour % 12 or 12}:{d:%M}{'am' if d.hour < 12 else 'pm'}"


def _span(delta: timedelta) -> str:
    hours, minutes = divmod(int(delta.total_seconds()) // 60, 60)
    return f"{hours}h {minutes}m"


def _moves(week: dict) -> str:
    pairs = zip(week.get("transfers_out", []), week.get("transfers_in", []))
    moves = "; ".join(f"{o['name']} out, {i['name']} in" for o, i in pairs)
    if not moves:
        return "No transfer, save it"
    return f"{moves} (a −{week['hit_cost']} hit)" if week.get("hits") else moves


def _chip(plan: dict) -> tuple:
    """(the chip to play with this plan's XI, or None; what to say about chips).

    The planner only prices a Free Hit, it doesn't pick the team, and the XI in
    the message is the one without it. So "play it" would be an order nobody
    could follow: GW10 2026-27 said so over a normal XI, for a gain of 2.4 points
    over playing it another week."""
    scenarios = (plan.get("chip_plan") or {}).get("scenarios") or [{}]
    for p in scenarios[0].get("plan", []):
        if not p.get("now"):
            continue
        if p["chip"] == "freehit":
            return None, (f"none. The planner rates a Free Hit +{p['value']} this week, "
                          "but it doesn't build that team, so this plan is without it")
        name = CHIP_NAMES.get(p["chip"], p["chip"])
        chip = f"{name} on {p['player']}" if p.get("player") else name
        return chip, chip
    return None, "none this week"


def _lineup(xi: list) -> str:
    lines = {}
    for p in xi:
        lines.setdefault(p["position"], []).append(p["name"])
    return "; ".join(", ".join(names) for names in lines.values())


def _news(plan: dict, players: list) -> str | None:
    """What the team-news reader says about the players in this plan."""
    ids = {p["player_id"] for p in players}
    calls = [f"{i['name']} {NEWS_WORDS[i['status']]}"
             for i in (plan.get("team_news") or {}).get("items", [])
             if i.get("player_id") in ids and i.get("status") in NEWS_WORDS]
    return ", ".join(calls) or None


def _marker(gameweek: int) -> str:
    return f"<!-- deadline-reminder gw{gameweek} -->"


def message(plan: dict, gameweek: int, deadline: datetime, now: datetime, owner: str = "",
            test: bool = False) -> str:
    """The comment. Its first line carries the whole call, because that's the
    line an email preview or a phone notification shows."""
    mention = f"@{owner} " if owner else ""
    left = _span(deadline - now)
    start = "Test, your real reminder looks like this. " if test else ""
    week = ((plan.get("transfer_plan") or {}).get("weeks") or [None])[0]

    if plan.get("gameweek") != gameweek or not week:
        lines = [f"{start}{mention}GW{gameweek} deadline in {left}, and there's no plan for it yet.",
                 "",
                 f"**Deadline:** {_clock(deadline)}",
                 "",
                 f"The refresh may be stuck, so check the site: {SITE_URL}"]
    else:
        players = plan["starting_xi"] + plan["bench"]
        names = {p["player_id"]: p["name"] for p in players}
        captain, vice = names.get(plan.get("captain_id"), "?"), names.get(plan.get("vice_captain_id"), "?")
        moves = _moves(week)
        chip, chip_line = _chip(plan)
        play = f" Play {chip}." if chip else ""
        lines = [f"{start}{mention}GW{gameweek} deadline in {left}: {moves}. {captain} captain.{play}",
                 "",
                 f"**Deadline:** {_clock(deadline)}",
                 f"**Transfers:** {moves}",
                 f"**Captain:** {captain}, **vice:** {vice}",
                 f"**Chip:** {chip_line}",
                 f"**XI:** {_lineup(plan['starting_xi'])}",
                 f"**Bench, in order:** {', '.join(p['name'] for p in plan['bench'])}"]
        hit = (plan.get("transfer_plan") or {}).get("hit_recommendation")
        if hit and hit.get("worth_it"):
            lines.append(f"**Also worth a −{hit['hit_cost']}:** {hit['verdict']}")
        news = _news(plan, players)
        if news:
            lines.append(f"**News:** {news}")
        age = now - _utc(plan["generated_at"])
        lines += ["",
                  f"Plan from {_span(age)} ago. It can still change before the deadline, "
                  f"so the site has the final word: {SITE_URL}"]
        if age > STALE_AFTER and not test:     # a test can run days before the refreshes start
            lines.append("That's older than it should be, so the refresh may be stuck.")
    if not test:
        lines += ["", _marker(gameweek)]
    return "\n".join(lines)


def _github(method: str, path: str, **kwargs):
    r = requests.request(method, f"{GITHUB_API}/repos/{os.environ['GITHUB_REPOSITORY']}/{path}",
                         headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                                  "Accept": "application/vnd.github+json"},
                         timeout=REQUEST_TIMEOUT, **kwargs)
    r.raise_for_status()
    return r.json()


def _issue() -> int:
    """The one issue the reminders go on, opened the first time it's needed."""
    params = {"state": "all", "sort": "created", "direction": "asc", "per_page": 100}
    for issue in _github("GET", "issues", params=params):
        if issue["title"] == REMINDER_ISSUE_TITLE and "pull_request" not in issue:
            return issue["number"]
    body = ("Each comment here is the plan as it stood 4-5 hours before that gameweek's "
            "deadline, posted by `backend/deadline_reminder.py`.")
    return _github("POST", "issues", json={"title": REMINDER_ISSUE_TITLE, "body": body})["number"]


def _already_sent(issue: int, gameweek: int, deadline: datetime) -> bool:
    # Only this week's comments: next season has a GW10 too.
    since = (deadline - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    comments = _github("GET", f"issues/{issue}/comments", params={"since": since, "per_page": 100})
    return any(_marker(gameweek) in c["body"] for c in comments)


def main(argv: list | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    preview, wait = "--preview" in argv, "--wait" in argv
    test = os.environ.get("TEST", "").lower() == "true"
    now = datetime.now(timezone.utc)
    plan = json.loads(FRONTEND_JSON_PATH.read_text())

    found = next_deadline(plan, now)
    if found is None:
        print("No deadlines left this season.", file=sys.stderr)
        return 0
    gameweek, deadline = found
    if wait:
        pause = None if test else time_to_wait(deadline, now)
        if pause:
            print(f"GW{gameweek}: waiting {_span(pause)} for the window to open.", file=sys.stderr)
            time.sleep(pause.total_seconds())
        return 0
    if not (preview or test or is_due(deadline, now)):
        print(f"GW{gameweek} deadline in {_span(deadline - now)}: too early to remind.", file=sys.stderr)
        return 0

    text = message(plan, gameweek, deadline, now, os.environ.get("GITHUB_REPOSITORY_OWNER", ""), test)
    if preview:
        print(text)
        return 0
    issue = _issue()
    if not test and _already_sent(issue, gameweek, deadline):
        print(f"GW{gameweek}: already reminded.", file=sys.stderr)
        return 0
    _github("POST", f"issues/{issue}/comments", json={"body": text})
    print(f"GW{gameweek}: reminder posted on issue #{issue}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
