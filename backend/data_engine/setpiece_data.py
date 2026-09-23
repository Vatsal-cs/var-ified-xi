"""
File: setpiece_data.py
Path: var-ified-xi/backend/data_engine/setpiece_data.py

Who takes the penalties, the free kicks and the corners.

This is the cheapest edge in fantasy football and the model has never seen it.
A penalty is roughly a 0.79 xG shot handed to one nominated player, and the
nomination is public: FPL publishes `penalties_order`, `direct_freekicks_order`
and `corners_and_indirect_freekicks_order` in the bootstrap payload this
pipeline already downloads every run.

Measured on this season's own data, attackers with 200+ minutes:

    first-choice penalty taker    5.28 pts/90    21.1 total
    not the taker                 4.32 pts/90    14.5 total

It was left out originally for a good reason: the vaastav archive that
supplies the training seasons has no set-piece columns, so a feature built
from the live bootstrap would exist at prediction time and not at training
time — the exact distribution mismatch this project avoids everywhere else.

That blocker is gone. olbauday/FPL-Core-Insights publishes the same three
fields SNAPSHOTTED PER GAMEWEEK, keyed on official FPL element ids, for
2024-25 and 2025-26. So the feature can be trained on honestly.

ENCODING

Raw order is 1, 2, 3... with nothing recorded for players who aren't in the
queue at all, which makes it awkward as a number: "not a taker" is worse than
first choice, but so is third choice, so the column isn't monotonic. Inverting
it fixes that — priority = 1/order, and 0 for everyone else:

    first choice   1.00
    second         0.50
    third          0.33
    not a taker    0.00

Monotonic, bounded, and it places the big gap where the real one is: between
taking them and not.

COVERAGE

2023-24 is not in FPL-Core-Insights, so rows from that season get zeros —
indistinguishable from "takes nothing". Whether that dilution costs more than
the feature gains is a question for backtest.py, not for this module.
"""

import io
import logging

import pandas as pd
import requests

from config import RAW_DIR, REQUEST_HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

BASE_URL = "https://raw.githubusercontent.com/olbauday/FPL-Core-Insights/main/data"

SETPIECE_FEATURE_COLUMNS = [
    "penalty_priority",
    "freekick_priority",
    "corner_priority",
]

# Every one of these is "this player takes none of them", which is true of
# roughly nine players in ten.
SETPIECE_NEUTRAL = {col: 0.0 for col in SETPIECE_FEATURE_COLUMNS}

_ORDER_COLUMNS = {
    "penalty_priority": "penalties_order",
    "freekick_priority": "direct_freekicks_order",
    "corner_priority": "corners_and_indirect_freekicks_order",
}


def _long_season(season: str) -> str:
    """'2024-25' -> '2024-2025', the layout this dataset uses."""
    start, end = season.split("-")
    return f"{start}-{start[:2]}{end}"


def _candidate_urls(season: str) -> list:
    """The file moved between seasons, so try both layouts."""
    long_name = _long_season(season)
    return [
        f"{BASE_URL}/{long_name}/playerstats.csv",
        f"{BASE_URL}/{long_name}/playerstats/playerstats.csv",
    ]


def _cache_path(season: str):
    return RAW_DIR / f"setpieces_{season}.csv"


def fetch_season_setpieces(season: str) -> pd.DataFrame:
    """Per-gameweek set-piece duties for one season.

    Returns columns [element, round, penalty_priority, freekick_priority,
    corner_priority], or an empty frame when the season isn't published —
    which is not an error, just a season this dataset doesn't cover.
    """
    cache = _cache_path(season)
    if cache.exists():
        return pd.read_csv(cache)

    raw = None
    for url in _candidate_urls(season):
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT * 4)
        except requests.RequestException as e:
            logger.warning("Set-piece fetch failed for %s (%s)", season, e)
            continue
        if resp.ok:
            raw = resp.text
            break

    if raw is None:
        logger.info("No set-piece data published for %s — feature will be zero "
                    "for those rows.", season)
        empty = pd.DataFrame(columns=["element", "round"] + SETPIECE_FEATURE_COLUMNS)
        cache.write_text(empty.to_csv(index=False))
        return empty

    df = pd.read_csv(io.StringIO(raw), low_memory=False)
    out = to_priorities(df, id_col="id", gw_col="gw")
    cache.write_text(out.to_csv(index=False))
    logger.info("Set-piece data %s: %d player-gameweeks with a duty recorded",
                season, int((out[SETPIECE_FEATURE_COLUMNS].sum(axis=1) > 0).sum()))
    return out


def to_priorities(df: pd.DataFrame, id_col: str = "id",
                  gw_col: str = "gw") -> pd.DataFrame:
    """Turns raw order columns into the 1/order priority encoding."""
    out = pd.DataFrame({
        "element": df[id_col].astype(int),
        "round": df[gw_col].astype(int) if gw_col in df.columns else 0,
    })
    for feature, source in _ORDER_COLUMNS.items():
        if source in df.columns:
            order = pd.to_numeric(df[source], errors="coerce")
            # 1/order, and 0 wherever no duty is recorded. Orders are >= 1, so
            # there is no division by zero to guard.
            out[feature] = (1.0 / order).fillna(0.0)
        else:
            out[feature] = 0.0
    return out.drop_duplicates(["element", "round"])


def from_bootstrap(bootstrap: dict) -> dict:
    """Today's set-piece duties, as {element_id: {feature: value}}.

    The live bootstrap carries only the CURRENT ordering, with no history, so
    this is a snapshot rather than a per-gameweek series. Applied to
    current-season training rows it credits a player retroactively for a job
    he may only have taken over recently; the historical seasons, which are
    most of the training data, carry the genuine per-gameweek values.
    """
    rows = pd.DataFrame(bootstrap["elements"])
    priorities = to_priorities(rows, id_col="id", gw_col="__none__")
    return priorities.set_index("element")[SETPIECE_FEATURE_COLUMNS].to_dict("index")
