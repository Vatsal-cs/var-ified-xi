"""
File: fetch_data.py
Path: var-ified-xi/backend/data_engine/fetch_data.py

Pulls raw data from the free, public FPL API:
  - bootstrap-static: all players, teams, current gameweek
  - fixtures: full season fixture list (for difficulty ratings)
  - element-summary/{id}: per-player gameweek-by-gameweek history

Everything is cached to backend/data/raw/ as JSON so repeated runs on the
same day don't hammer the API.
"""

import json
import time
import logging
from datetime import date

import requests

from config import (
    BOOTSTRAP_URL,
    FIXTURES_URL,
    ELEMENT_SUMMARY_URL,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
    REQUEST_DELAY,
    RAW_DIR,
)

logger = logging.getLogger(__name__)


def _get(url: str) -> dict:
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _cache_path(name: str) -> "Path":
    return RAW_DIR / f"{name}_{date.today().isoformat()}.json"


def fetch_bootstrap_static(use_cache: bool = True) -> dict:
    """Players, teams, positions, current gameweek metadata."""
    path = _cache_path("bootstrap_static")
    if use_cache and path.exists():
        logger.info("Loading bootstrap-static from cache: %s", path)
        return json.loads(path.read_text())

    logger.info("Fetching bootstrap-static from FPL API...")
    data = _get(BOOTSTRAP_URL)
    path.write_text(json.dumps(data))
    return data


def fetch_fixtures(use_cache: bool = True) -> list:
    """Full season fixture list, including FDR (difficulty) ratings."""
    path = _cache_path("fixtures")
    if use_cache and path.exists():
        logger.info("Loading fixtures from cache: %s", path)
        return json.loads(path.read_text())

    logger.info("Fetching fixtures from FPL API...")
    data = _get(FIXTURES_URL)
    path.write_text(json.dumps(data))
    return data


def fetch_element_summary(player_id: int) -> dict:
    """Per-player gameweek history + upcoming fixtures. No caching per-player
    (too many small files); the full history set is cached as one blob by
    fetch_all_player_histories instead.
    """
    url = ELEMENT_SUMMARY_URL.format(player_id=player_id)
    return _get(url)


def fetch_all_player_histories(player_ids: list, use_cache: bool = True) -> dict:
    """Returns {player_id: element_summary_json} for every player.

    This is the slowest call (one request per player, ~600+ players), so it
    is cached as a single JSON blob for the day.
    """
    path = _cache_path("player_histories")
    if use_cache and path.exists():
        logger.info("Loading player histories from cache: %s", path)
        raw = json.loads(path.read_text())
        return {int(k): v for k, v in raw.items()}

    logger.info("Fetching per-player history for %d players (this takes a while)...", len(player_ids))
    histories = {}
    for i, pid in enumerate(player_ids):
        try:
            histories[pid] = fetch_element_summary(pid)
        except requests.RequestException as e:
            logger.warning("Failed to fetch player %s: %s", pid, e)
            histories[pid] = {"history": [], "fixtures": []}
        time.sleep(REQUEST_DELAY)
        if (i + 1) % 50 == 0:
            logger.info("  ...%d/%d players fetched", i + 1, len(player_ids))

    path.write_text(json.dumps(histories))
    return histories
