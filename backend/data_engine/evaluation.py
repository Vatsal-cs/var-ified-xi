"""
File: evaluation.py
Path: var-ified-xi/backend/data_engine/evaluation.py

How a research result becomes a verdict.

The old rule was "a change ships if it scores more points in every season
tested", on one run with one random seed. Measured on 8 Oct 2026: changing
NOTHING but XGBoost's seed moved the two-season production backtest between
4,443 and 4,618 points, and in 3 of 6 seed pairs one seed "won both seasons".
A change that does nothing passed the old rule half the time, and every
points verdict in the ledger at the time sat inside that noise.

So both harnesses now run each variant over several seeds and hand their
per-gameweek points to this module, which reports:

  * the mean and spread across seeds, per season;
  * the paired difference to a reference (production), averaged over seeds
    gameweek by gameweek, with a block-bootstrap 95% interval;
  * how many (season, seed) cells the variant won;
  * a verdict, decided by rules written down before the run:

        better     pooled interval above zero AND ahead in every season
        worse      pooled interval below zero AND behind in every season
        no detectable effect   anything else

"No detectable effect" is not "rejected". It means the harness can't tell,
which is a statement about the harness's resolution as much as the change.

WHY BLOCKS

Gameweeks aren't independent draws. In the season simulator a different
squad carries forward for weeks, so one decision shows up as a run of
correlated differences; resampling single gameweeks would treat that run as
many independent wins and make the interval too narrow. Resampling
contiguous blocks keeps those runs together. The backtest rebuilds its squad
every week, so its blocks can be short.

Results are written as JSON (--out on either harness) so runs made on
different machines, or on different days, can be pooled:

    python -m data_engine.evaluation results/*.json --reference production
"""

import argparse
import json
import math
from collections import defaultdict

import numpy as np

RESAMPLES = 4000
CONFIDENCE = 0.95


def _paired_series(runs: list, variant: str, reference: str, season: str):
    """Per-gameweek (variant - reference), averaged over the seeds both ran.

    Only gameweeks and seeds present for both are used, so a partial run
    can't manufacture a difference.
    """
    by = defaultdict(dict)
    for r in runs:
        if r["season"] == season and r["variant"] in (variant, reference):
            by[r["variant"]][r["seed"]] = dict(map(tuple, r["per_gw"]))
    seeds = sorted(set(by[variant]) & set(by[reference]))
    if not seeds:
        return None, []
    gws = sorted(set.intersection(*[set(by[variant][s]) & set(by[reference][s])
                                    for s in seeds]))
    diffs = np.array([[by[variant][s][g] - by[reference][s][g] for g in gws]
                      for s in seeds], dtype=float)
    return diffs, seeds


def block_bootstrap_totals(series: np.ndarray, block: int, rng) -> np.ndarray:
    """Resampled season totals of a per-gameweek series, using circular
    blocks of `block` consecutive gameweeks."""
    n = len(series)
    if n == 0:
        return np.zeros(RESAMPLES)
    block = max(1, min(block, n))
    n_blocks = math.ceil(n / block)
    starts = rng.integers(0, n, size=(RESAMPLES, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    idx = idx.reshape(RESAMPLES, -1)[:, :n]
    return series[idx].sum(axis=1)


def compare(runs: list, variant: str, reference: str, seasons: list,
            block: int = 2, seed: int = 0) -> dict:
    """The paired comparison of one variant against the reference."""
    rng = np.random.default_rng(seed)
    per_season, pooled_draws, cells_won, cells = {}, None, 0, 0
    for season in seasons:
        diffs, seeds = _paired_series(runs, variant, reference, season)
        if diffs is None:
            continue
        mean_series = diffs.mean(axis=0)
        draws = block_bootstrap_totals(mean_series, block, rng)
        pooled_draws = draws if pooled_draws is None else pooled_draws + draws
        totals = diffs.sum(axis=1)
        cells += len(totals)
        cells_won += int((totals > 0).sum())
        lo, hi = np.quantile(draws, [(1 - CONFIDENCE) / 2, (1 + CONFIDENCE) / 2])
        per_season[season] = {
            "diff": float(mean_series.sum()),
            "ci": [float(lo), float(hi)],
            "seeds": seeds,
            "gameweeks": int(diffs.shape[1]),
        }

    if not per_season:
        return {"variant": variant, "reference": reference, "verdict": "not run"}

    pooled = sum(s["diff"] for s in per_season.values())
    lo, hi = np.quantile(pooled_draws, [(1 - CONFIDENCE) / 2, (1 + CONFIDENCE) / 2])
    signs = [s["diff"] for s in per_season.values()]
    if lo > 0 and all(d > 0 for d in signs):
        verdict = "better"
    elif hi < 0 and all(d < 0 for d in signs):
        verdict = "worse"
    else:
        verdict = "no detectable effect"

    return {
        "variant": variant,
        "reference": reference,
        "pooled_diff": float(pooled),
        "pooled_ci": [float(lo), float(hi)],
        "per_season": per_season,
        "cells_won": cells_won,
        "cells": cells,
        "verdict": verdict,
    }


def season_table(runs: list) -> list:
    """Mean and spread across seeds, per (variant, season)."""
    groups = defaultdict(list)
    for r in runs:
        groups[(r["variant"], r["season"])].append(r)
    rows = []
    for (variant, season), rs in sorted(groups.items()):
        totals = np.array([r["total"] for r in rs], dtype=float)
        row = {
            "variant": variant, "season": season, "seeds": len(rs),
            # A variant that can't train in a season's first week skips it,
            # so its total covers fewer gameweeks. The paired comparison only
            # uses gameweeks both ran; this column says when totals don't.
            "gws": int(np.median([len(r["per_gw"]) for r in rs])),
            "mean": float(totals.mean()),
            "sd": float(totals.std(ddof=1)) if len(rs) > 1 else 0.0,
            "min": float(totals.min()), "max": float(totals.max()),
        }
        for metric in ("mae", "spearman", "brier60", "hits", "transfers"):
            vals = [r[metric] for r in rs if r.get(metric) is not None]
            if vals:
                row[metric] = float(np.mean(vals))
        rows.append(row)
    return rows


def print_report(runs: list, reference: str, block: int, title: str) -> list:
    seasons = sorted({r["season"] for r in runs})
    variants = list(dict.fromkeys(r["variant"] for r in runs))
    width = 92

    print()
    print("=" * width)
    print(title)
    print("=" * width)
    print(f"{'variant':<20}{'season':<9}{'seeds':>6}{'GWs':>5}{'mean':>9}{'sd':>7}"
          f"{'range':>13}{'MAE':>7}{'rank-r':>8}{'Brier60':>9}")
    print("-" * width)
    for row in season_table(runs):
        rng_txt = f"{row['min']:.0f}-{row['max']:.0f}"
        print(f"{row['variant'][:19]:<20}{row['season']:<9}{row['seeds']:>6}{row['gws']:>5}"
              f"{row['mean']:>9.1f}{row['sd']:>7.1f}{rng_txt:>13}"
              f"{row.get('mae', float('nan')):>7.3f}"
              f"{row.get('spearman', float('nan')):>8.3f}"
              f"{row.get('brier60', float('nan')):>9.4f}")

    comparisons = []
    if reference in variants:
        print("-" * width)
        print(f"Paired against {reference}, per-gameweek, averaged over seeds "
              f"(block bootstrap, {block}-GW blocks, {int(CONFIDENCE * 100)}% CI):")
        for variant in variants:
            if variant == reference:
                continue
            c = compare(runs, variant, reference, seasons, block=block)
            comparisons.append(c)
            if c["verdict"] == "not run":
                continue
            seasons_txt = "  ".join(
                f"{s} {v['diff']:+.0f} [{v['ci'][0]:+.0f},{v['ci'][1]:+.0f}]"
                for s, v in c["per_season"].items())
            print(f"  {variant:<18} pooled {c['pooled_diff']:+7.1f} "
                  f"[{c['pooled_ci'][0]:+.0f}, {c['pooled_ci'][1]:+.0f}]  "
                  f"won {c['cells_won']}/{c['cells']} cells  -> {c['verdict'].upper()}")
            print(f"  {'':<18} {seasons_txt}")
    print("=" * width)
    print("better = pooled CI above zero and ahead in every season; worse = the")
    print("mirror image; anything else is no detectable effect, not a rejection.")
    print()
    return comparisons


def load(paths: list) -> list:
    runs = []
    for p in paths:
        with open(p) as fh:
            runs.extend(json.load(fh)["runs"])
    # The same (variant, season, seed) run twice — say, in two pooled files —
    # counts once: the later file wins.
    unique = {(r["variant"], r["season"], r["seed"]): r for r in runs}
    return list(unique.values())


def main():
    parser = argparse.ArgumentParser(description="Pool harness results into a verdict.")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--reference", default="production")
    parser.add_argument("--block", type=int, default=2,
                        help="bootstrap block length in gameweeks (season_sim: use 4)")
    parser.add_argument("--variants", nargs="*",
                        help="only these variants (the reference is always kept)")
    args = parser.parse_args()
    runs = load(args.files)
    if args.variants:
        keep = set(args.variants) | {args.reference}
        runs = [r for r in runs if r["variant"] in keep]
    print_report(runs, args.reference, args.block,
                 title=f"POOLED RESULTS ({len(args.files)} file(s))")


if __name__ == "__main__":
    main()
