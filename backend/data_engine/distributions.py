"""
File: distributions.py
Path: var-ified-xi/backend/data_engine/distributions.py

A full points distribution for every player, not just an average.

The model gives an expected score ("4.3 points"), which hides the thing that
decides close calls: how spread out the outcomes are. A defender who scores 2
or 6 and a forward who scores 2 or 13 can share an average and be very
different bets. With a distribution per player you can say "Haaland outscores
Saka 64% of the time" or "Groß has an 18% chance of 10+", and know when a
start/bench call is really a coin flip.

How it's built. The model already splits a match into two parts:
  * will he play — P(no minutes), P(cameo, under 60), P(60+), after the
    injury flags;
  * if he plays 60+, how many points on average — the points-if-60+ value.
The second is a single number, so it's turned into a distribution from what
actually happened before: across every match of the last two seasons, the
model's walk-forward projections (made without seeing the result) were
grouped by position and by points-if-60+, and each group's real scores were
counted. A player projected 5.1 if he plays gets the distribution of real
scores of players the model projected about 5.1. Cameos get their position's
cameo distribution, no minutes is 0. A double gameweek adds two matches.

The tables are fitted once (python -m data_engine.distributions --build ...)
and saved to data/points_distributions.json; the fit and its out-of-sample
checks are in research/2026-10-distributions.
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)

TABLES_PATH = config.BACKEND_ROOT / "data" / "points_distributions.json"

# Scores from -3 (a red card and a miss) to 30; anything beyond sits in the end
# cells. Index i is a score of i + SUPPORT_MIN.
SUPPORT_MIN, SUPPORT_MAX = -3, 30
SIZE = SUPPORT_MAX - SUPPORT_MIN + 1

# Groups by points-if-60+, per position: quantile edges, finer at the top where
# the captaincy calls live and the scores spread out most.
QUANTILES = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, .95, .98, 1.0]
MIN_GROUP = 60          # smaller groups merge into their neighbour


def _hist(points) -> np.ndarray:
    idx = np.clip(np.asarray(points, dtype=int) - SUPPORT_MIN, 0, SIZE - 1)
    h = np.bincount(idx, minlength=SIZE).astype(float)
    return h / h.sum()


# ---------------------------------------------------------------------------
# Fitting
# ---------------------------------------------------------------------------
def build_tables(rows: pd.DataFrame) -> dict:
    """From walk-forward rows (one per player-match: element_type, pts_if_60,
    minutes, actual) to {"full": {pos: {"centers", "pmf", "n"}}, "cameo": {pos: pmf}}."""
    out = {"support_min": SUPPORT_MIN, "support_max": SUPPORT_MAX, "full": {}, "cameo": {}}
    for pos in (1, 2, 3, 4):
        played = rows[(rows["element_type"] == pos) & (rows["minutes"] >= 60)]
        cameo = rows[(rows["element_type"] == pos) & rows["minutes"].between(1, 59)]
        edges = np.unique(played["pts_if_60"].quantile(QUANTILES).to_numpy())
        groups = pd.cut(played["pts_if_60"], edges, include_lowest=True)
        centers, pmfs, ns = [], [], []
        pending = []
        for _, g in played.groupby(groups, observed=True):
            pending.append(g)
            merged = pd.concat(pending)
            if len(merged) >= MIN_GROUP:
                centers.append(float(merged["pts_if_60"].mean()))
                pmfs.append(_hist(merged["actual"]))
                ns.append(len(merged))
                pending = []
        if pending and pmfs:            # a short last group joins the one before
            merged = pd.concat(pending)
            n = ns[-1] + len(merged)
            centers[-1] = (centers[-1] * ns[-1] + merged["pts_if_60"].sum()) / n
            pmfs[-1] = (pmfs[-1] * ns[-1] + _hist(merged["actual"]) * len(merged)) / n
            ns[-1] = n
        out["full"][str(pos)] = {"centers": [round(c, 4) for c in centers],
                                 "pmf": [[round(float(x), 6) for x in p] for p in pmfs],
                                 "n": ns}
        out["cameo"][str(pos)] = [round(float(x), 6) for x in _hist(cameo["actual"])]
    return out


def load_tables(path: Path = TABLES_PATH) -> dict | None:
    if not path.exists():
        logger.warning("No points distributions at %s; skipping probabilities.", path)
        return None
    t = json.loads(path.read_text())
    for pos, tab in t["full"].items():
        tab["centers"] = np.asarray(tab["centers"])
        tab["pmf"] = np.asarray(tab["pmf"])
    t["cameo"] = {pos: np.asarray(p) for pos, p in t["cameo"].items()}
    return t


# ---------------------------------------------------------------------------
# One player
# ---------------------------------------------------------------------------
def _shift(p: np.ndarray, d: float) -> np.ndarray:
    """p moved d points along the score axis; a fractional move is a mix of
    the two whole-point moves around it, so scores stay whole numbers."""
    lo = int(np.floor(d))
    f = d - lo
    out = np.zeros(SIZE)
    for k, w in ((lo, 1 - f), (lo + 1, f)):
        if w <= 0:
            continue
        idx = np.clip(np.arange(SIZE) + k, 0, SIZE - 1)
        np.add.at(out, idx, p * w)
    return out


def full_pmf(tables: dict, element_type: int, pts_if_60: float) -> np.ndarray:
    """Distribution of a 60+ minute match for this position and projection:
    between two groups, a blend of both; beyond the ends, the end group moved."""
    tab = tables["full"][str(int(element_type))]
    c, P = tab["centers"], tab["pmf"]
    x = float(pts_if_60)
    if x <= c[0]:
        return _shift(P[0], x - c[0])
    if x >= c[-1]:
        return _shift(P[-1], x - c[-1])
    k = int(np.searchsorted(c, x))
    w = (x - c[k - 1]) / (c[k] - c[k - 1])
    return (1 - w) * P[k - 1] + w * P[k]


def match_pmf(tables: dict, element_type: int, p_full: float, p_cameo: float,
              pts_if_60: float) -> np.ndarray:
    """One match. p_full and p_cameo are AFTER injury flags (they need not sum
    to 1; the rest is no minutes, which scores 0)."""
    p_full, p_cameo = max(0.0, float(p_full)), max(0.0, float(p_cameo))
    zero = np.zeros(SIZE)
    zero[-SUPPORT_MIN] = 1.0
    return ((1 - p_full - p_cameo) * zero
            + p_cameo * tables["cameo"][str(int(element_type))]
            + p_full * full_pmf(tables, element_type, pts_if_60))


def combine(pmfs: list) -> np.ndarray:
    """A double gameweek: the sum of two matches' scores."""
    if not pmfs:
        z = np.zeros(SIZE)
        z[-SUPPORT_MIN] = 1.0
        return z
    total = pmfs[0]
    for p in pmfs[1:]:
        conv = np.convolve(total, p)            # support starts at 2*SUPPORT_MIN
        idx = np.clip(np.arange(len(conv)) + SUPPORT_MIN, 0, SIZE - 1)
        total = np.zeros(SIZE)
        np.add.at(total, idx, conv)
    return total


def summary(p: np.ndarray) -> dict:
    scores = np.arange(SUPPORT_MIN, SUPPORT_MAX + 1)
    cdf = np.cumsum(p)
    return {
        "mean": round(float((p * scores).sum()), 2),
        "p10": int(scores[np.searchsorted(cdf, 0.10)]),
        "p90": int(scores[np.searchsorted(cdf, 0.90)]),
        "p_blank": round(float(p[scores <= 2].sum()), 3),
        "p_return": round(float(p[scores >= 6].sum()), 3),
        "p_haul": round(float(p[scores >= 10].sum()), 3),
    }


# ---------------------------------------------------------------------------
# Comparisons
# ---------------------------------------------------------------------------
# Head-to-head chances straight from two distributions came out overconfident
# on the season they weren't fitted on (a "70%" favourite won ~65%), though
# each player's own range and 10+ chance were honest. Scaling the log-odds by
# this factor, fitted on both seasons' pairs, brings 2025-26 within 2 points
# in every bin and 2024-25 within 3 up to 70% (research/2026-10-distributions).
PAIR_LOGIT_SCALE = 0.73


def beats(a: np.ndarray, b: np.ndarray) -> tuple:
    """(P(a > b), P(a == b)) for two independent players, uncalibrated."""
    cdf_b = np.cumsum(b)
    below_b = np.concatenate([[0.0], cdf_b[:-1]])
    return float((a * below_b).sum()), float((a * b).sum())


def head_to_head(a: np.ndarray, b: np.ndarray, scale: float = PAIR_LOGIT_SCALE) -> float:
    """P(a outscores b), ties left out, recalibrated."""
    ab, ba = beats(a, b)[0], beats(b, a)[0]
    if ab + ba <= 0:
        return 0.5
    p = min(max(ab / (ab + ba), 1e-6), 1 - 1e-6)
    return float(1 / (1 + np.exp(-scale * np.log(p / (1 - p)))))


# ---------------------------------------------------------------------------
# Production: every player's next-gameweek distribution
# ---------------------------------------------------------------------------
def next_gameweek_pmfs(tables: dict, fixture_predictions: pd.DataFrame, gameweek: int) -> dict:
    """{player_id: pmf} for the next gameweek, from predict_points' per-match
    rows (p_full, p_cameo, pts_if_60, avail_factor). No row: a blank, all 0."""
    rows = fixture_predictions
    if "gw" in rows.columns:
        rows = rows[rows["gw"] == gameweek]
    out = {}
    for pid, g in rows.groupby("player_id"):
        f = g["avail_factor"].to_numpy(float)
        out[int(pid)] = combine([
            match_pmf(tables, et, pf * fa, pc * fa, x)
            for et, pf, pc, x, fa in zip(g["element_type"], g["p_full"], g["p_cameo"],
                                         g["pts_if_60"], f)
        ])
    return out


def payload(p: np.ndarray) -> dict:
    """What the dashboard gets per player: the headline numbers, plus the
    distribution itself from 0 points up (negative scores folded into 0 — they
    only matter for the sign of a tie, never for a choice) so the page can
    compare any two players itself."""
    s = summary(p)
    zero = -SUPPORT_MIN
    pmf = np.concatenate([[p[:zero + 1].sum()], p[zero + 1:]])
    s["pmf"] = [round(float(x), 4) for x in pmf]
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fit the points-distribution tables.")
    ap.add_argument("--build", nargs="+", required=True,
                    help="walk-forward rows CSVs (research/2026-10-projection-bias/collect.py)")
    ap.add_argument("--out", default=str(TABLES_PATH))
    args = ap.parse_args(argv)
    rows = pd.concat([pd.read_csv(p) for p in args.build], ignore_index=True)
    tables = build_tables(rows)
    Path(args.out).write_text(json.dumps(tables))
    for pos, tab in tables["full"].items():
        print(f"position {pos}: {len(tab['centers'])} groups, centers "
              f"{tab['centers'][0]:.2f}..{tab['centers'][-1]:.2f}, n={sum(tab['n'])}")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
