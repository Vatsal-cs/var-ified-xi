"""The pre-registered Europe-midweek bias check (PREREGISTRATION.md).

    python research/2026-10-europe-bias/analyze.py
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = os.path.join(HERE, "..", "2026-10-projection-bias", "rows_{}_om.csv")
REPS = 2000


def load():
    frames = []
    for season in ("2024-25", "2025-26"):
        f = pd.read_csv(ROWS.format(season))
        f["season"] = season
        frames.append(f)
    d = pd.concat(frames, ignore_index=True)
    d = d[d["pred"] >= 2.5].copy()
    d["res"] = d["actual"] - d["pred"]
    d["played60"] = (d["minutes"] >= 60).astype(float)
    recent = d["xm_days_before"] <= 4
    d["group"] = np.where(recent & (d["xm_started_before"] == 1), "S started it",
                 np.where(recent & (d["xm_rested_before"] == 1), "R rested from it",
                 np.where(d["xm_days_before"] > 7, "N no midweek game", "other")))
    return d


def boot(d, stat):
    keys = (d["season"] + ":" + d["round"].astype(str)).to_numpy()
    codes, uniq = pd.factorize(keys)
    rng = np.random.default_rng(0)
    point = stat(d, np.ones(len(d)))
    draws = []
    for _ in range(REPS):
        cnt = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))
        draws.append(stat(d, cnt[codes].astype(float)))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return round(float(point), 3), [round(float(lo), 3), round(float(hi), 3)]


def main():
    d = load()
    base = (d["group"] == "N no midweek game").to_numpy()
    print(f"{'group':<20}{'n':>7}{'pred':>7}{'actual':>8}{'res':>7}{'P60 pred':>10}{'P60 real':>10}")
    for g in ("S started it", "R rested from it", "N no midweek game"):
        m = d["group"] == g
        x = d[m]
        print(f"{g:<20}{len(x):>7}{x.pred.mean():>7.2f}{x.actual.mean():>8.2f}{x.res.mean():>7.2f}"
              f"{x.p60.mean():>10.3f}{x.played60.mean():>10.3f}")
    print()
    for g in ("S started it", "R rested from it"):
        m = (d["group"] == g).to_numpy()
        res = boot(d, lambda f, w: (w * m * f.res).sum() / (w * m).sum() - (w * base * f.res).sum() / (w * base).sum())
        p60 = boot(d, lambda f, w: (w * m * (f.played60 - f.p60)).sum() / (w * m).sum())
        bias = (abs(res[0]) >= 0.3 and (res[1][0] > 0 or res[1][1] < 0)) or \
               (abs(p60[0]) >= 0.05 and (p60[1][0] > 0 or p60[1][1] < 0))
        print(f"{g}: residual vs no-midweek {res[0]:+.3f} {res[1]};  real-minus-predicted P(60+) "
              f"{p60[0]:+.3f} {p60[1]}  ->  {'BIAS' if bias else 'no bias found'}")


if __name__ == "__main__":
    main()
