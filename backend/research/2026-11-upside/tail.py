"""How often each variant has a huge season, from the backtest's weekly scores.

A season is rebuilt by drawing two-gameweek blocks with replacement (the same
blocks and the same seed for every variant, so the comparison is paired).
"Huge" is the reference's own top 1% of such seasons. Prints, per season and
pooled, each variant's chance of a huge season and its average gain or loss.

    python research/2026-11-upside/tail.py research/2026-11-upside/up_*.json
"""
import json
import sys

import numpy as np

REFERENCE, DRAWS, BLOCK, TOP = "lagged_ratings", 20000, 2, 0.99


def load(paths):
    weeks = {}          # (season, variant) -> {seed: np.array of weekly points by gw order}
    for p in paths:
        for r in json.load(open(p))["runs"]:
            pts = np.array([w[1] for w in sorted(r["per_gw"])], dtype=float)
            weeks.setdefault((r["season"], r["variant"]), {})[r["seed"]] = pts
    return weeks


def seasons(weeks, season, variants, rng):
    seeds = sorted(weeks[(season, REFERENCE)])
    n = len(weeks[(season, REFERENCE)][seeds[0]])
    starts = np.arange(0, n - BLOCK + 1)
    nblocks = int(np.ceil(n / BLOCK))
    pick_seed = rng.choice(seeds, DRAWS)
    pick_start = rng.choice(starts, (DRAWS, nblocks))
    idx = (pick_start[:, :, None] + np.arange(BLOCK)).reshape(DRAWS, -1)[:, :n]
    out = {}
    for v in variants:
        mat = np.stack([weeks[(season, v)][s] for s in pick_seed])
        out[v] = np.take_along_axis(mat, idx, axis=1).sum(axis=1)
    return out


def main(paths):
    weeks = load(paths)
    rng = np.random.default_rng(2026)
    season_names = sorted({s for s, _ in weeks})
    variants = sorted({v for _, v in weeks}, key=lambda v: (v != REFERENCE, v))
    pooled = {v: [] for v in variants}
    for season in season_names:
        totals = seasons(weeks, season, variants, rng)
        cut = np.quantile(totals[REFERENCE], TOP)
        print(f"\n{season}: huge season = {cut:.0f}+ (the reference's top 1%)")
        for v in variants:
            p = (totals[v] >= cut).mean()
            diff = (totals[v] - totals[REFERENCE]).mean()
            pooled[v].append((p, diff))
            print(f"  {v:<16} chance {100 * p:5.2f}%   average {diff:+6.1f}")
    print("\nPooled (mean of seasons):")
    for v in variants:
        ps, ds = zip(*pooled[v])
        print(f"  {v:<16} chance {100 * np.mean(ps):5.2f}%   average {np.mean(ds):+6.1f}")


if __name__ == "__main__":
    main(sys.argv[1:])
