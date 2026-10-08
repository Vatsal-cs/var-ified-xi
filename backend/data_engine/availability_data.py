"""
File: availability_data.py
Path: var-ified-xi/backend/data_engine/availability_data.py

What FPL said about each player's fitness BEFORE each past deadline.

Production scales every projection by FPL's injury flags (status and
chance_of_playing, see train_model.predict_points). The vaastav archive the
research harnesses replay has no flags at all, so every backtest until now
scored a weaker model than the one that ships: one that walks into a
gameweek not knowing who is injured. Measured on 2025-26 GW20-38, the
flagless model's P(60+) Brier is 0.0842 against 0.0778 with production's
rule applied.

olbauday/FPL-Core-Insights publishes FPL's player payload snapshotted once
per gameweek for 2024-25 and 2025-26, keyed on official element ids. The
snapshot labelled gameweek t is taken AFTER t is played (its cumulative
points match "through t" for 99.7% of 2025-26 rows and 99.9% of 2024-25), so
it is exactly what a manager could read before the t+1 deadline. That is the
join used here: snapshot t -> gameweek t+1. Joining it to t itself would
hand the model news written after the matches it is predicting.

Coverage limits, stated plainly:

  * 2022-23 and 2023-24 have no snapshots. Those seasons run flagless, so a
    comparison across seasons with and without flags compares harnesses,
    not models.
  * A player missing from the previous snapshot (signed that week, say) is
    treated as fit. That's ~0.4% of rows.
  * The snapshot time within the gap between gameweeks isn't published. It
    is after the last match of t; it may occasionally be after news that
    broke later in the week, which would flatter the flags slightly.
"""

import io
import logging

import pandas as pd
import requests

from config import RAW_DIR, REQUEST_HEADERS, REQUEST_TIMEOUT
from data_engine.setpiece_data import _candidate_urls

logger = logging.getLogger(__name__)

# A player with no flag. Matches production, where a missing
# chance_of_playing is read as 100 (train_model.predict_points).
FIT_STATUS = "a"
FIT_CHANCE = 100.0

def _cache_path(season: str):
    return RAW_DIR / f"availability_{season}.csv"


def fetch_season_availability(season: str) -> pd.DataFrame:
    """Per-gameweek flags for one season, keyed on the gameweek they were
    known BEFORE: columns [element, round, status, chance_of_playing, news].

    Empty (not an error) for a season the dataset doesn't cover.
    """
    cache = _cache_path(season)
    if cache.exists():
        return pd.read_csv(cache, keep_default_na=False, na_values=[""])

    raw = None
    for url in _candidate_urls(season):
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT * 4)
        except requests.RequestException as e:
            logger.warning("Availability fetch failed for %s (%s)", season, e)
            continue
        if resp.ok:
            raw = resp.text
            break

    if raw is None:
        logger.info("No availability snapshots for %s — that season runs "
                    "without injury flags.", season)
        empty = pd.DataFrame(columns=["element", "round", "status",
                                      "chance_of_playing", "news"])
        cache.write_text(empty.to_csv(index=False))
        return empty

    out = from_playerstats(pd.read_csv(io.StringIO(raw), low_memory=False))
    cache.write_text(out.to_csv(index=False))
    logger.info("Availability %s: %d player-gameweeks, %d flagged",
                season, len(out), int((out["status"] != FIT_STATUS).sum()))
    return out


def from_playerstats(df: pd.DataFrame) -> pd.DataFrame:
    """FPL-Core-Insights playerstats rows -> flags keyed on the gameweek they
    were known before."""
    out = pd.DataFrame({
        "element": df["id"].astype(int),
        # Snapshot after gameweek t is the news going into t + 1.
        "round": df["gw"].astype(int) + 1,
        "status": df["status"].fillna(FIT_STATUS).astype(str),
        "chance_of_playing": pd.to_numeric(df["chance_of_playing_next_round"],
                                           errors="coerce"),
        "news": df["news"] if "news" in df.columns else "",
    })
    return out.drop_duplicates(["element", "round"], keep="last")


def attach(df: pd.DataFrame, season: str) -> float:
    """Adds `status` and `chance_of_playing` to rows carrying `element` and
    `round`, in place, as they stood before that round's deadline. Returns
    the share of rows that found a snapshot (0.0 for an uncovered season).

    Call this AFTER add_rolling_features: that function fills every NaN with
    zero, and a chance_of_playing of 0 means "won't play".
    """
    flags = fetch_season_availability(season)
    df["status"] = FIT_STATUS
    df["chance_of_playing"] = FIT_CHANCE
    if flags.empty or "element" not in df.columns:
        return 0.0

    lut = flags.set_index(["element", "round"])[["status", "chance_of_playing"]]
    keys = pd.MultiIndex.from_arrays([df["element"].astype(int),
                                      df["round"].astype(int)])
    joined = lut.reindex(keys)
    matched = joined["status"].notna().to_numpy()
    df["status"] = joined["status"].fillna(FIT_STATUS).to_numpy()
    # FPL leaves chance empty for an unflagged player; that is 100, not 0.
    df["chance_of_playing"] = joined["chance_of_playing"].fillna(FIT_CHANCE).to_numpy()
    return float(matched.mean()) if len(matched) else 0.0
