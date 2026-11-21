"""
File: deadline_snapshot.py
Path: var-ified-xi/backend/data_engine/deadline_snapshot.py

Saves, before each FPL deadline, data that can't be got back afterwards:

1. FPL's own view at the deadline: every player's status, chance of
   playing, news, price, ownership and FPL's expected points. The archive
   only keeps end-of-season values, and its xP column was recorded after
   lineups were known, which is why it can't be used as a benchmark.
   Rewritten on every run until the deadline, so the last one before it is
   kept.
2. Bookmakers' player odds for the gameweek's matches (The Odds API):
   anytime goalscorer, assists and shots on target. Free plans give current
   odds only, so a season of these has to be collected as it happens before
   it can be tested (research/2026-11-model-audit). Fetched once per
   gameweek, in the last ODDS_WINDOW_HOURS before the deadline, and only if
   ODDS_API_KEY is set (a free key, kept in GitHub secrets).

Files go to data/deadline/<season>/gw<NN>_fpl.json.gz and gw<NN>_odds.json.gz.
Nothing here feeds the model yet.

    python -m data_engine.deadline_snapshot
"""

import gzip
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_engine import fetch_data  # noqa: E402

logger = logging.getLogger(__name__)

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "deadline"
ODDS_API = "https://api.the-odds-api.com/v4/sports/soccer_epl"
ODDS_MARKETS = "player_goal_scorer_anytime,player_assists,player_shots_on_target"
ODDS_REGIONS = "us"  # soccer player props come from US bookmakers only
ODDS_WINDOW_HOURS = 10
# The free plan has 500 credits a month and a gameweek costs about 30
# (three markets x ten matches); stop well before running out.
ODDS_MIN_CREDITS = 100
FPL_WINDOW_HOURS = 30

PLAYER_FIELDS = ["id", "web_name", "team", "element_type", "status",
                 "chance_of_playing_next_round", "chance_of_playing_this_round",
                 "news", "news_added", "now_cost", "selected_by_percent", "ep_next",
                 "ep_this", "form", "points_per_game", "total_points", "minutes",
                 "transfers_in_event", "transfers_out_event",
                 "penalties_order", "corners_and_indirect_freekicks_order",
                 "direct_freekicks_order"]
TEAM_FIELDS = ["id", "name", "short_name", "strength", "strength_attack_home",
               "strength_attack_away", "strength_defence_home", "strength_defence_away"]


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def season_label(bootstrap: dict) -> str:
    first = min(_parse(e["deadline_time"]) for e in bootstrap["events"] if e.get("deadline_time"))
    return f"{first.year}-{(first.year + 1) % 100:02d}"


def next_deadline(bootstrap: dict, now: datetime):
    """(gameweek, its deadline, the following deadline or None)."""
    events = sorted(((e["id"], _parse(e["deadline_time"])) for e in bootstrap["events"]
                     if e.get("deadline_time")), key=lambda p: p[1])
    upcoming = [i for i, (_, d) in enumerate(events) if d > now]
    if not upcoming:
        return None
    i = upcoming[0]
    following = events[i + 1][1] if i + 1 < len(events) else None
    return events[i][0], events[i][1], following


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"), sort_keys=True)


def fpl_snapshot(bootstrap: dict, fixtures: list, gameweek: int, now: datetime) -> dict:
    return {
        "saved_at": now.isoformat(),
        "gameweek": gameweek,
        "players": [{k: p.get(k) for k in PLAYER_FIELDS} for p in bootstrap["elements"]],
        "teams": [{k: t.get(k) for k in TEAM_FIELDS} for t in bootstrap["teams"]],
        "fixtures": [f for f in fixtures if f.get("event") == gameweek],
    }


def _odds_get(url: str, key: str, **params):
    """GET with the key as a parameter. Errors are logged by status only, so
    the key (part of the URL) never reaches a log."""
    try:
        r = requests.get(url, params={"apiKey": key, **params}, timeout=30)
    except requests.RequestException as e:
        logger.warning("Odds request failed (%s).", type(e).__name__)
        return None, None
    remaining = r.headers.get("x-requests-remaining")
    if r.status_code != 200:
        logger.warning("Odds request returned HTTP %s.", r.status_code)
        return None, remaining
    return r.json(), remaining


def gameweek_events(events: list, deadline: datetime, following) -> list:
    """Matches kicking off after this deadline and before the next one."""
    out = []
    for e in events:
        ko = _parse(e["commence_time"])
        if ko > deadline and (following is None or ko < following):
            out.append(e)
    return out


def odds_snapshot(key: str, deadline: datetime, following, now: datetime):
    events, remaining = _odds_get(f"{ODDS_API}/events", key)
    if events is None:
        return None
    matches = gameweek_events(events, deadline, following)
    saved = []
    for e in matches:
        if remaining is not None and float(remaining) < ODDS_MIN_CREDITS:
            logger.warning("Only %s odds credits left; stopping.", remaining)
            break
        odds, remaining = _odds_get(f"{ODDS_API}/events/{e['id']}/odds", key,
                                    regions=ODDS_REGIONS, markets=ODDS_MARKETS,
                                    oddsFormat="decimal")
        if odds is not None:
            saved.append(odds)
    logger.info("Saved player odds for %d of %d matches; %s credits left.",
                len(saved), len(matches), remaining)
    return {"saved_at": now.isoformat(), "markets": ODDS_MARKETS, "regions": ODDS_REGIONS,
            "credits_remaining": remaining, "events": saved}


def main(now: datetime = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    now = now or datetime.now(timezone.utc)
    bootstrap = fetch_data.fetch_bootstrap_static(use_cache=False)
    nd = next_deadline(bootstrap, now)
    if nd is None:
        logger.info("No deadlines left this season.")
        return 0
    gameweek, deadline, following = nd
    hours = (deadline - now).total_seconds() / 3600
    folder = OUT_DIR / season_label(bootstrap)

    if hours <= FPL_WINDOW_HOURS:
        fixtures = fetch_data.fetch_fixtures(use_cache=False)
        _write(folder / f"gw{gameweek:02d}_fpl.json.gz",
               fpl_snapshot(bootstrap, fixtures, gameweek, now))
        logger.info("Saved FPL's deadline view for GW%d (%.1fh before).", gameweek, hours)

    key = os.environ.get("ODDS_API_KEY", "").strip()
    odds_path = folder / f"gw{gameweek:02d}_odds.json.gz"
    if not key:
        logger.info("No ODDS_API_KEY; player odds not saved.")
    elif hours <= ODDS_WINDOW_HOURS and not odds_path.exists():
        snap = odds_snapshot(key, deadline, following, now)
        if snap and snap["events"]:
            _write(odds_path, snap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
