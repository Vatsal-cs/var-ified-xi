"""
File: team_news.py
Path: var-ified-xi/backend/data_engine/team_news.py

Reads the latest team news before FPL does.

FPL's injury flags are the model's only view of who's fit, and they lag:
they're updated by hand, often hours after a manager's press conference, and
they never say "fit but likely to be benched". This asks an AI model with web
search — Google's Gemini 2.5 Flash with Google Search, free, or Claude if
that key is set instead — to read the news for the clubs that matter to you — your squad, the
players the plan wants to buy, the Wildcard squad — and report each player
as out, doubtful, rotation risk or expected to start, with a source.

What it changes, deliberately narrow:
  * "out" and "doubtful" feed the projection the same way an FPL flag would
    (chance of playing 0, or the reported chance), but only when they're
    WORSE than FPL's own flag and come with a source from the last few days.
    That's the information FPL itself would publish a few hours later.
  * "rotation risk" is shown, never applied. Predicted line-ups are guesses,
    and nothing here has been tested against what happened.
There are no archived press conferences to backtest on, so the reader is
judged live: every call it makes is saved with the source, for checking
against who actually played (research/2026-10-team-news).

Needs GEMINI_API_KEY (free from aistudio.google.com: Gemini 2.5 Flash with
Google Search grounding is free up to 500 requests a day; a run uses ~4) or
ANTHROPIC_API_KEY (paid, ~$0.30-1 a run). Without either, nothing runs and
the dashboard says so. Runs only when a deadline is close
(TEAM_NEWS_WINDOW_HOURS) and reuses a fresh result for TEAM_NEWS_TTL_HOURS.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests

import config

logger = logging.getLogger(__name__)

API_URL = "https://api.anthropic.com/v1/messages"
STATUSES = ("out", "doubtful", "rotation_risk", "expected_to_start", "no_news")
APPLIED = ("out", "doubtful")
CLUBS_PER_CALL = 4

SYSTEM = """You check Premier League team news for Fantasy Premier League managers.
Use web search to find the most recent news: manager press conferences, club
injury updates, suspensions, and reputable outlets (BBC Sport, Sky Sports, The
Athletic, the Guardian, premierleague.com, club websites). Only use news
published in the last 7 days. Never guess: if you find nothing recent about a
player, his status is "no_news". Statuses:
  out               - ruled out of this match (injury, illness, suspension, not in squad)
  doubtful          - a genuine fitness or availability doubt for this match
  rotation_risk     - fit, but credible reporting says he may be benched or rested
  expected_to_start - fit and expected to start
  no_news           - nothing recent found
Reply with one JSON object in a ```json block and nothing after it."""


def _now():
    return datetime.now(timezone.utc)


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def provider() -> str | None:
    """Which model reads the news: Gemini when its (free) key is set, else
    Claude when its key is, else none."""
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    return None


def model_name() -> str | None:
    return {"gemini": config.TEAM_NEWS_GEMINI_MODEL, "claude": config.TEAM_NEWS_MODEL}.get(provider())


def enabled() -> bool:
    return provider() is not None and config.TEAM_NEWS_ENABLED


def _prompt(clubs: list, gameweek: int, deadline: str) -> str:
    lines = [f"Today is {_now():%A %d %B %Y, %H:%M} UTC. Gameweek {gameweek} deadline: {deadline}.",
             "Find the latest team news for each club below, ahead of its match. Report on",
             "every listed player, and add any other player at these clubs who is ruled out.", ""]
    for c in clubs:
        lines.append(f"- {c['club']} ({c['fixture']}):")
        lines += [f"    {p['name']} (id {p['player_id']}, {p['position']})" for p in c["players"]]
    lines += ["", "JSON shape:",
              '{"players": [{"player_id": <id from the list, or null>, "name": "...", "club": "...",',
              '  "status": "out|doubtful|rotation_risk|expected_to_start|no_news",',
              '  "start_chance": <0-100, your estimate he starts>, "reason": "<= 120 chars",',
              '  "source_url": "https://...", "source_date": "YYYY-MM-DD"}]}']
    return "\n".join(lines)


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _call_gemini(prompt: str) -> tuple:
    """One Gemini call grounded in Google Search. Returns (text, sources),
    sources being the pages Google actually returned: [(title, url)]."""
    body = {"systemInstruction": {"parts": [{"text": SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192}}
    url = GEMINI_URL.format(model=config.TEAM_NEWS_GEMINI_MODEL)
    headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "content-type": "application/json"}
    for attempt in range(3):
        r = requests.post(url, headers=headers, json=body, timeout=180)
        if r.status_code == 429:                       # free tier: a few requests a minute
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        cand = (r.json().get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        chunks = (cand.get("groundingMetadata") or {}).get("groundingChunks", [])
        sources = [(c["web"].get("title", ""), c["web"].get("uri", "")) for c in chunks if c.get("web")]
        return text, sources
    raise RuntimeError("team news: Gemini rate limit")


def _keep_sources(items: list, sources: list) -> list:
    """Only a call backed by a page Google returned can lower a projection:
    an item's link is kept if its site is among those pages, swapped for the
    matching (or first) returned page otherwise, and cleared when the model
    didn't search at all."""
    if not sources:
        for it in items:
            it["source_url"] = None
        return items
    for it in items:
        host = _host(it.get("source_url") or "")
        if host and any(host in (t or "").lower() or host in _host(u) for t, u in sources):
            continue
        it["source_url"] = sources[0][1]
    return items


def _call(prompt: str) -> str:
    """One Messages API call with web search; returns the final text. Follows
    pause_turn (a long search turn the API hands back to be continued)."""
    headers = {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    messages = [{"role": "user", "content": prompt}]
    body = {"model": config.TEAM_NEWS_MODEL, "max_tokens": 4096, "system": SYSTEM,
            "tools": [{"type": "web_search_20260209", "name": "web_search",
                       "max_uses": config.TEAM_NEWS_MAX_SEARCHES}]}
    for _ in range(4):
        r = requests.post(API_URL, headers=headers, json={**body, "messages": messages}, timeout=300)
        r.raise_for_status()
        msg = r.json()
        if msg.get("stop_reason") != "pause_turn":
            return "".join(b.get("text", "") for b in msg["content"] if b.get("type") == "text")
        messages = messages + [{"role": "assistant", "content": msg["content"]}]
    raise RuntimeError("team news: search turn never finished")


def parse(text: str, known_ids: set) -> list:
    """The reply's JSON, cleaned: known statuses only, chances clamped, ids
    checked against the players asked about (None if he wasn't on the list)."""
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S) or re.search(r"(\{.*\})", text, re.S)
    if not m:
        raise ValueError("no JSON in the reply")
    items = []
    for p in json.loads(m.group(1)).get("players", []):
        status = str(p.get("status", "")).strip().lower()
        if status not in STATUSES:
            continue
        pid = p.get("player_id")
        try:
            pid = int(pid) if pid is not None else None
        except (TypeError, ValueError):
            pid = None
        try:
            chance = max(0, min(100, int(p.get("start_chance"))))
        except (TypeError, ValueError):
            chance = None
        url = str(p.get("source_url") or "")
        items.append({
            "player_id": pid if pid in known_ids else None,
            "name": str(p.get("name", ""))[:40],
            "club": str(p.get("club", ""))[:30],
            "status": status,
            "start_chance": chance,
            "reason": str(p.get("reason", ""))[:160],
            "source_url": url if url.startswith("http") else None,
            "source_date": str(p.get("source_date") or "")[:10] or None,
        })
    return items


def fetch(clubs: list, gameweek: int, deadline: str) -> dict:
    """clubs: [{"club", "fixture", "players": [{player_id, name, position}]}]."""
    known = {p["player_id"] for c in clubs for p in c["players"]}
    items, errors = [], []
    use = provider()
    for i in range(0, len(clubs), CLUBS_PER_CALL):
        chunk = clubs[i:i + CLUBS_PER_CALL]
        try:
            prompt = _prompt(chunk, gameweek, deadline)
            if use == "gemini":
                text, sources = _call_gemini(prompt)
                items += _keep_sources(parse(text, known), sources)
                time.sleep(5)                            # stay inside the free per-minute limit
            else:
                items += parse(_call(prompt), known)
        except Exception as e:                       # one club group failing isn't fatal
            errors.append(f"{', '.join(c['club'] for c in chunk)}: {e}")
            logger.warning("Team news for %s failed: %s", [c["club"] for c in chunk], e)
    return {"gameweek": gameweek, "fetched_at": _now().isoformat(), "model": model_name(),
            "clubs": [c["club"] for c in clubs], "items": items, "errors": errors}


def load_cached(gameweek: int) -> dict | None:
    path = config.TEAM_NEWS_PATH
    if not path.exists():
        return None
    try:
        news = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return news if news.get("gameweek") == gameweek else None


def get(clubs: list, gameweek: int, deadline: datetime, force: bool = False) -> dict | None:
    """This gameweek's news: fetched if a deadline is close and the cache is
    stale, else whatever was cached for this gameweek (or None)."""
    cached = load_cached(gameweek)
    if not enabled():
        return cached
    fresh = cached and _now() - datetime.fromisoformat(cached["fetched_at"]) < \
        timedelta(hours=config.TEAM_NEWS_TTL_HOURS)
    near = deadline - _now() < timedelta(hours=config.TEAM_NEWS_WINDOW_HOURS)
    if fresh or not (near or force):
        return cached
    logger.info("Reading team news for %d clubs...", len(clubs))
    news = fetch(clubs, gameweek, deadline.isoformat())
    config.TEAM_NEWS_PATH.write_text(json.dumps(news, indent=1))
    _log_calls(news)
    return news


def _log_calls(news: dict) -> None:
    """Every call, kept for the live check against who actually played."""
    path = config.TEAM_NEWS_LOG_PATH
    try:
        log = json.loads(path.read_text()) if path.exists() else []
    except (OSError, json.JSONDecodeError):
        log = []
    log.append({k: news[k] for k in ("gameweek", "fetched_at", "model", "items")})
    path.write_text(json.dumps(log[-60:], indent=1))


def apply(predict_df, news: dict | None, gameweek: int, max_age_days: int = 4) -> list:
    """Out / doubtful calls lower FPL's chance of playing for this gameweek's
    rows, in place, when they're worse than FPL's own flag and recent.
    Returns what was applied, for the dashboard."""
    if not news or not config.TEAM_NEWS_ADJUST or predict_df is None or predict_df.empty:
        return []
    applied = []
    today = _now().date()
    rows_gw = predict_df["gw"] == gameweek if "gw" in predict_df.columns else True
    for item in news.get("items", []):
        pid, status = item.get("player_id"), item.get("status")
        if pid is None or status not in APPLIED or not item.get("source_url"):
            continue
        try:
            age = (today - datetime.fromisoformat(item["source_date"]).date()).days
        except (TypeError, ValueError):
            continue
        if age > max_age_days:
            continue
        chance = 0 if status == "out" else max(25, min(75, item.get("start_chance") or 50))
        mask = (predict_df["player_id"] == pid) & rows_gw
        if not mask.any():
            continue
        fpl = predict_df.loc[mask, "chance_of_playing"].iloc[0]
        fpl_chance = 100 if fpl is None or fpl != fpl else float(fpl)      # NaN -> fit
        if chance >= fpl_chance:
            continue
        predict_df.loc[mask, "chance_of_playing"] = chance
        applied.append({"player_id": pid, "status": status, "chance": chance,
                        "fpl_chance": int(fpl_chance)})
    return applied
