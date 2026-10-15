"""Are the points distributions honest? Fit on one season, check on the other.

    python research/2026-10-distributions/validate.py

Uses the walk-forward rows from research/2026-10-projection-bias/collect.py
(projections made without seeing the result). Checks, written in
README.md before this was first run:
  1. The 10th-90th percentile range holds the real score >= 80% of the time.
  2. "Chance of 10+" matches how often 10+ happened, by tenths of prediction.
  3. "A outscores B" — for two players in the same gameweek, both projected
     2.5+ — matches how often A did outscore B (ties left out), in bins of 0.1.
Single-match gameweeks only, to keep each check about one distribution.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np
import pandas as pd

from data_engine import distributions as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = os.path.join(HERE, "..", "2026-10-projection-bias", "rows_{}.csv")
SEASONS = ["2024-25", "2025-26"]


def rows(season):
    f = pd.read_csv(ROWS.format(season))
    single = f.groupby(["player_id", "round"])["player_id"].transform("size") == 1
    return f[single].reset_index(drop=True)


def pmfs_for(tables, f):
    return np.stack([D.match_pmf(tables, et, p60, pc, x)
                     for et, p60, pc, x in zip(f["element_type"], f["p60"], f["p_cameo"], f["pts_if_60"])])


def check(fit_season, test_season, out):
    tables = D.build_tables(pd.read_csv(ROWS.format(fit_season)))
    for t in tables["full"].values():
        t["centers"], t["pmf"] = np.asarray(t["centers"]), np.asarray(t["pmf"])
    tables["cameo"] = {k: np.asarray(v) for k, v in tables["cameo"].items()}
    f = rows(test_season)
    P = pmfs_for(tables, f)
    scores = np.arange(D.SUPPORT_MIN, D.SUPPORT_MAX + 1)
    cdf = P.cumsum(1)
    p10 = scores[(cdf < 0.10).sum(1)]
    p90 = scores[(cdf < 0.90).sum(1)]
    a = f["actual"].to_numpy()
    pool = f["pred"].to_numpy() >= 2.5
    res = {"fit": fit_season, "test": test_season, "rows": int(len(f)), "pool_rows": int(pool.sum())}

    # 1. range coverage (all rows, and the pool)
    inside = (a >= p10) & (a <= p90)
    res["range_coverage_all"] = round(float(inside.mean()), 3)
    res["range_coverage_pool"] = round(float(inside[pool].mean()), 3)

    # 2. P(10+) calibration in the pool, by tenths of the prediction
    ph = P[:, scores >= 10].sum(1)
    d = pd.DataFrame({"p": ph[pool], "y": (a[pool] >= 10).astype(float)})
    d["bin"] = pd.qcut(d["p"], 10, duplicates="drop")
    res["haul"] = [{"pred": round(g["p"].mean(), 3), "actual": round(g["y"].mean(), 3), "n": len(g)}
                   for _, g in d.groupby("bin", observed=True)]

    # 3. pairwise, same gameweek, pool only
    below = np.concatenate([np.zeros((len(P), 1)), cdf[:, :-1]], axis=1)
    preds, wins = [], []
    for _, g in f[pool].groupby("round"):
        idx = g.index.to_numpy()
        i, j = np.triu_indices(len(idx), 1)
        i, j = idx[i], idx[j]
        p_ab = (P[i] * below[j]).sum(1)
        p_ba = (P[j] * below[i]).sum(1)
        keep = a[i] != a[j]
        preds.append((p_ab / (p_ab + p_ba))[keep])
        wins.append((a[i] > a[j])[keep].astype(float))
    pr, w = np.concatenate(preds), np.concatenate(wins)
    # fold so every pair reads "the favourite", 0.5-1.0
    fav = np.where(pr >= 0.5, pr, 1 - pr)
    won = np.where(pr >= 0.5, w, 1 - w)
    bins = np.arange(0.5, 1.0001, 0.05)
    res["pairs"] = int(len(pr))
    res["pairwise"] = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (fav >= lo) & (fav < hi if hi < 1 else fav <= hi)
        if m.sum() >= 200:
            res["pairwise"].append({"bin": f"{lo:.2f}-{hi:.2f}", "pred": round(float(fav[m].mean()), 3),
                                    "actual": round(float(won[m].mean()), 3), "n": int(m.sum())})
    res["pairwise_brier"] = round(float(((pr - w) ** 2).mean()), 4)
    res["pairwise_brier_coinflip"] = 0.25
    out.append(res)
    return pr, w


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def fit_scale(pr, w):
    """The log-odds scale that best fits (lowest log loss) — added after the
    first run showed the raw head-to-heads overconfident."""
    grid = np.arange(0.3, 1.21, 0.01)
    loss = [-(w * np.log(q) + (1 - w) * np.log(1 - q)).mean()
            for q in (1 / (1 + np.exp(-a * _logit(pr))) for a in grid)]
    return float(grid[int(np.argmin(loss))])


def recalibrated(pr, w, scale):
    q = 1 / (1 + np.exp(-scale * _logit(pr)))
    fav, won = np.where(q >= 0.5, q, 1 - q), np.where(q >= 0.5, w, 1 - w)
    rows = []
    bins = np.arange(0.5, 1.0001, 0.05)
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (fav >= lo) & (fav < hi if hi < 1 else fav <= hi)
        if m.sum() >= 200:
            rows.append({"bin": f"{lo:.2f}-{hi:.2f}", "pred": round(float(fav[m].mean()), 3),
                         "actual": round(float(won[m].mean()), 3), "n": int(m.sum())})
    return {"brier": round(float(((q - w) ** 2).mean()), 4), "bins": rows}


def main():
    out = []
    pairs = [check(SEASONS[0], SEASONS[1], out), check(SEASONS[1], SEASONS[0], out)]
    fitted = fit_scale(np.concatenate([p for p, _ in pairs]), np.concatenate([w for _, w in pairs]))
    for r, (pr, w) in zip(out, pairs):
        r["recalibrated"] = recalibrated(pr, w, D.PAIR_LOGIT_SCALE)
    with open(os.path.join(HERE, "results.json"), "w") as fh:
        json.dump({"fitted_pair_logit_scale": fitted, "shipped": D.PAIR_LOGIT_SCALE, "checks": out},
                  fh, indent=1)
    for r in out:
        print(f"\nfit {r['fit']} -> test {r['test']}  ({r['rows']} matches, {r['pool_rows']} in pool, {r['pairs']} pairs)")
        print(f"  10-90 range holds the real score: {r['range_coverage_all']:.1%} of all, "
              f"{r['range_coverage_pool']:.1%} of pool")
        print("  chance of 10+  predicted vs actual:",
              ", ".join(f"{h['pred']:.2f}/{h['actual']:.2f}" for h in r["haul"]))
        print(f"  A outscores B  Brier {r['pairwise_brier']} (coin flip 0.25)")
        for p in r["pairwise"]:
            print(f"     {p['bin']}  predicted {p['pred']:.3f}  actual {p['actual']:.3f}  n={p['n']}")
        rc = r["recalibrated"]
        print(f"  recalibrated (log-odds x {D.PAIR_LOGIT_SCALE}): Brier {rc['brier']}")
        for p in rc["bins"]:
            print(f"     {p['bin']}  predicted {p['pred']:.3f}  actual {p['actual']:.3f}  n={p['n']}")
    print(f"\nlog-odds scale fitted on both seasons' pairs: {fitted:.2f} (shipped {D.PAIR_LOGIT_SCALE})")


if __name__ == "__main__":
    main()
