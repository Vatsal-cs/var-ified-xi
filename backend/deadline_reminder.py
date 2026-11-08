"""
File: deadline_reminder.py
Path: var-ified-xi/backend/deadline_reminder.py

Tells you what to do before each FPL deadline, without opening the site.

Runs on GitHub Actions (.github/workflows/deadline-reminder.yml). The first run
inside the last REMINDER_HOURS before a deadline posts the week's plan as a
comment on one GitHub issue, mentioning the repo's owner. GitHub turns the
mention into an email and a push on its mobile app, so this needs no mail
account, no key and no money: the workflow's own token is enough.

A deadline before REMINDER_EARLY_HOUR your time would put that in the night, so
the first one goes out at REMINDER_EVENING_HOUR the evening before instead
(config.evening_before), once the news has been read just before it.

The schedule asks for hourly, but GitHub's scheduler doesn't keep to that: in
the first days the job ran every 5-8 hours. So a run that lands in the hours
before the window waits for it (--wait), and then reads the newest plan.

A second comment follows once the news has been read for the last time, about
two hours before the deadline (final_refresh.py), saying what changed since the
first, or that nothing did.

Each goes out once a gameweek, however many runs land in the window. The comments
already on the issue are the record of that, so there's no state to commit.

    python deadline_reminder.py --preview    # prints the message, sends nothing
    python deadline_reminder.py --wait       # sleeps until the window, if it opens soon
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from config import (BOOTSTRAP_URL, FRONTEND_JSON_PATH, REMINDER_EVENING_READ_MINUTES, REMINDER_HOURS,
                    REMINDER_ISSUE_TITLE, REMINDER_MAX_WAIT_HOURS, REMINDER_UTC_OFFSET, REQUEST_HEADERS,
                    REQUEST_TIMEOUT, SITE_URL, TEAM_NEWS_FINAL_READ_HOURS, TEAM_NEWS_PATH, evening_before)

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


def first_reminder_at(deadline: datetime) -> datetime:
    return evening_before(deadline) or deadline - timedelta(hours=REMINDER_HOURS)


def is_due(deadline: datetime, now: datetime, read_at: datetime | None = None) -> bool:
    """Is the first reminder due? An evening one goes out as soon as the news
    read just before it is in (final_refresh.py starts it), or at the hour
    without it if that read never came."""
    at = first_reminder_at(deadline)
    if evening_before(deadline):
        read_by = at - timedelta(minutes=REMINDER_EVENING_READ_MINUTES)
        return now >= at or (now >= read_by and read_at is not None and read_at >= read_by)
    return now >= at


def time_to_wait(at: datetime, now: datetime) -> timedelta | None:
    """How long until `at`, if a run should wait that long."""
    wait = at - now
    return wait if timedelta(0) < wait <= timedelta(hours=REMINDER_MAX_WAIT_HOURS) else None


def last_read() -> datetime | None:
    """When the team news was last read, from the file each refresh commits."""
    try:
        return _utc(json.loads(TEAM_NEWS_PATH.read_text())["fetched_at"])
    except (OSError, KeyError, ValueError):
        return None


def is_final(deadline: datetime, now: datetime, read_at: datetime | None) -> bool:
    """Has the last news read of the week happened? Then the second reminder is due."""
    mark = deadline - timedelta(hours=TEAM_NEWS_FINAL_READ_HOURS)
    return now >= mark and read_at is not None and read_at >= mark


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


def _free_hit(plan: dict) -> dict | None:
    """The Free Hit team, when the chip plan says to play it this week."""
    fh = plan.get("free_hit") or {}
    return fh if fh.get("play") and fh.get("gameweek") == plan.get("gameweek") and fh.get("starting_xi") else None


def _chip(plan: dict) -> tuple:
    """(the chip to play, or None; what to say about chips).

    A Free Hit is only ordered with its team (plan["free_hit"]), which the
    message then gives in place of your own XI. Without one, "play it" would be
    an order nobody could follow: GW10 2026-27 said so over a normal XI."""
    fh = _free_hit(plan)
    if fh:
        return "your Free Hit", f"Free Hit, +{fh['gain']} on your own XI this week"
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


def _marker(gameweek: int, final: bool = False) -> str:
    return f"<!-- deadline-reminder gw{gameweek}{' final' if final else ''} -->"


def _line(lines: list, label: str) -> str | None:
    return next((l[len(label):].strip() for l in lines if l.startswith(label)), None)


def _same(label: str, old: str | None, new: str | None) -> bool:
    if old is None or new is None:
        return old == new
    if label == "**XI:**":                  # the same XI, listed in another order
        return set(re.split(r"[;,]\s*", old)) == set(re.split(r"[;,]\s*", new))
    # A Free Hit's rated value moves with every refresh; that isn't a change of plan.
    return re.sub(r"[\d.]+", "", old) == re.sub(r"[\d.]+", "", new) if label == "**Chip:**" else old == new


def _changes(earlier: str, lines: list) -> list:
    """What the first reminder said that this one doesn't."""
    labels = {"**Transfers:**": "transfers", "**Captain:**": "captain", "**Chip:**": "chip",
              "**XI:**": "XI", "**Bench, in order:**": "bench order"}
    old = earlier.splitlines()
    return [name for label, name in labels.items()
            if not _same(label, _line(old, label), _line(lines, label))]


def message(plan: dict, gameweek: int, deadline: datetime, now: datetime, owner: str = "",
            test: bool = False, final: bool = False, earlier: str | None = None) -> str:
    """The comment. Its first line carries the whole call, because that's the
    line an email preview or a phone notification shows. final: the second
    reminder, compared against earlier, the first one's text."""
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
        fh = _free_hit(plan)
        team = fh or plan
        players = team["starting_xi"] + team["bench"]
        names = {p["player_id"]: p["name"] for p in players}
        captain, vice = names.get(team.get("captain_id"), "?"), names.get(team.get("vice_captain_id"), "?")
        chip, chip_line = _chip(plan)
        if fh:
            free = (plan.get("team") or {}).get("free_transfers", 1)
            moves = (f"None of your own. The Free Hit team is for this week only: your squad comes "
                     f"back for GW{gameweek + 1} with {free} free transfer{'s' if free != 1 else ''}, as now")
            call = f"Play your Free Hit. {captain} captain."
        else:
            moves = _moves(week)
            play = f" Play {chip}." if chip else ""
            call = f"{moves}. {captain} captain.{play}"
        lines = [f"{start}{mention}GW{gameweek} deadline in {left}: {call}",
                 "",
                 f"**Deadline:** {_clock(deadline)}",
                 f"**Transfers:** {moves}",
                 f"**Captain:** {captain}, **vice:** {vice}",
                 f"**Chip:** {chip_line}",
                 f"**XI:** {_lineup(team['starting_xi'])}",
                 f"**Bench, in order:** {', '.join(p['name'] for p in team['bench'])}"]
        hit = (plan.get("transfer_plan") or {}).get("hit_recommendation")
        if hit and hit.get("worth_it") and not fh:
            lines.append(f"**Also worth a −{hit['hit_cost']}:** {hit['verdict']}")
        news = _news(plan, players)
        if news:
            lines.append(f"**News:** {news}")
        age = now - _utc(plan["generated_at"])
        if final:
            changed = _changes(earlier, lines) if earlier else None
            state = "" if changed is None else ": nothing changed since your last reminder"
            if changed:
                state = f": changed since your last reminder: {', '.join(changed)}"
            lines[0] = f"{mention}GW{gameweek} final plan, deadline in {left}{state}. {call}"
            if changed and "transfers" in changed:
                lines.append("If you've already made the earlier transfer, another one costs a −4.")
            if (plan.get("team_news") or {}).get("errors"):
                lines.append("Some clubs' news couldn't be read this time.")
            lines += ["", f"Plan from {_span(age)} ago, after the last news read. "
                          f"The site has the final word: {SITE_URL}"]
        else:
            lines += ["", f"Plan from {_span(age)} ago. It can still change before the deadline, "
                          f"so the site has the final word: {SITE_URL}"]
        if age > STALE_AFTER and not test:     # a test can run days before the refreshes start
            lines.append("That's older than it should be, so the refresh may be stuck.")
    if not test:
        lines += ["", _marker(gameweek, final)]
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
    body = ("Each comment here is the plan as it stood before that gameweek's deadline: first "
            "about 5 hours before it (9pm the evening before, for a deadline before 9am), then "
            "after the last news read about 2 hours before it. Posted by `backend/deadline_reminder.py`.")
    return _github("POST", "issues", json={"title": REMINDER_ISSUE_TITLE, "body": body})["number"]


def _this_weeks_comments(issue: int, deadline: datetime) -> list:
    # Only this week's: next season has a GW10 too.
    since = (deadline - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    comments = _github("GET", f"issues/{issue}/comments", params={"since": since, "per_page": 100})
    return [c["body"] for c in comments]


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
        pause = None if test else time_to_wait(first_reminder_at(deadline), now)
        if pause:
            print(f"GW{gameweek}: waiting {_span(pause)} for the window to open.", file=sys.stderr)
            time.sleep(pause.total_seconds())
        return 0
    if not (preview or test or is_due(deadline, now, last_read())):
        print(f"GW{gameweek} deadline in {_span(deadline - now)}: too early to remind.", file=sys.stderr)
        return 0

    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    final = not test and is_final(deadline, now, last_read())
    if preview:
        print(message(plan, gameweek, deadline, now, owner, test, final))
        return 0
    issue = _issue()
    bodies = [] if test else _this_weeks_comments(issue, deadline)
    # Once the second has gone out, a late first would only say it again.
    done = [_marker(gameweek, True)] if final else [_marker(gameweek), _marker(gameweek, True)]
    if any(m in b for m in done for b in bodies):
        print(f"GW{gameweek}: already reminded.", file=sys.stderr)
        return 0
    earlier = next((b for b in bodies if _marker(gameweek) in b), None)
    text = message(plan, gameweek, deadline, now, owner, test, final, earlier)
    _github("POST", f"issues/{issue}/comments", json={"body": text})
    print(f"GW{gameweek}: reminder posted on issue #{issue}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
