"""
File: injury_log.py
Path: var-ified-xi/backend/data_engine/injury_log.py

Persists a lightweight record of which players have been flagged as
fitness-doubtful (injured, suspended, or given a chance-of-playing
percentage below 100) EACH TIME main.py runs. This is deliberately
separate from the day-cached RAW_DIR pulls: those get overwritten every
day, but this log accumulates across the whole season.

Why this exists: a player who's been flagged 4 separate times this
season is a real recurring-fitness-concern signal that a single
"currently available" snapshot completely misses. FPL's API only ever
tells you today's status — it has no memory. This gives the pipeline
one.

Deliberately NOT used as a trained XGBoost feature (see config.py's
REPEAT_FLAG_THRESHOLD comment) — we don't have this history for past
gameweeks retroactively, so folding it into training would create a
train/predict skew where every historical row shows "0 flags" and only
live predictions ever show a nonzero count. Instead it's applied as an
extra dampening multiplier at prediction time only, alongside the
existing status/chance_of_playing dampening in train_model.py.
"""

import json
import logging
from datetime import date

from config import INJURY_LOG_PATH

logger = logging.getLogger(__name__)


def _load_log() -> dict:
    if INJURY_LOG_PATH.exists():
        try:
            return json.loads(INJURY_LOG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("Injury log unreadable, starting fresh: %s", INJURY_LOG_PATH)
    return {}


def _save_log(log: dict) -> None:
    INJURY_LOG_PATH.write_text(json.dumps(log, indent=2))


def update_injury_log(bootstrap: dict) -> None:
    """Scans today's bootstrap-static snapshot and appends a flag entry for
    every player currently marked doubtful. Deduplicates by date, so
    running main.py multiple times on the same day only logs once.
    """
    log = _load_log()
    today = date.today().isoformat()

    for player in bootstrap["elements"]:
        pid = str(player["id"])
        status = player.get("status", "a")
        chance = player.get("chance_of_playing_next_round")

        is_doubtful = status != "a" or (chance is not None and chance < 100)
        if not is_doubtful:
            continue

        entries = log.setdefault(pid, [])
        if entries and entries[-1]["date"] == today:
            continue  # already logged today

        entries.append({"date": today, "status": status, "chance": chance})

    _save_log(log)


def get_flag_counts() -> dict:
    """Returns {player_id: number of distinct days flagged this season}."""
    log = _load_log()
    return {int(pid): len(entries) for pid, entries in log.items()}