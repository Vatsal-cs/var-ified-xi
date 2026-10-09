"""Seed averaging: apply the pre-registered criteria to the backtest runs.

    python research/2026-10-seed-averaging/stability.py "bag_*.json"
"""
import glob
import itertools
import os
import sys

import numpy as np
import pandas as pd

SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SP, "..", ".."))
from data_engine import evaluation  # noqa: E402

pattern = sys.argv[1] if len(sys.argv) > 1 else "bag_*.json"
runs = evaluation.load(sorted(glob.glob(f"{SP}/{pattern}")))
seasons = sorted({r["season"] for r in runs})

comp = evaluation.print_report(runs, "production", 2, "SEED AVERAGING — bagged5 vs production")


def stability(variant, season):
    rs = [r for r in runs if r["variant"] == variant and r["season"] == season]
    picks = {r["seed"]: {g: (set(xi or []), cap) for g, xi, cap in r.get("picks", [])} for r in rs}
    xi_overlap, cap_agree = [], []
    for a, b in itertools.combinations(sorted(picks), 2):
        for g in set(picks[a]) & set(picks[b]):
            (xa, ca), (xb, cb) = picks[a][g], picks[b][g]
            if xa and xb:
                xi_overlap.append(len(xa & xb) / 11)
                cap_agree.append(ca == cb)
    totals = [r["total"] for r in rs]
    return {"seeds": len(rs), "xi_overlap": float(np.mean(xi_overlap)) if xi_overlap else float("nan"),
            "captain_agree": float(np.mean(cap_agree)) if cap_agree else float("nan"),
            "n_cap": len(cap_agree), "cap_hits": int(np.sum(cap_agree)),
            "total_sd": float(np.std(totals, ddof=1)) if len(totals) > 1 else float("nan")}


rows = []
for season in seasons:
    for v in ("production", "bagged5"):
        st = stability(v, season)
        t = next((x for x in evaluation.season_table(runs) if x["variant"] == v and x["season"] == season), {})
        rows.append({"season": season, "variant": v, **st, "mae": t.get("mae"), "brier60": t.get("brier60"),
                     "mean": t.get("mean")})
df = pd.DataFrame(rows)
print(df.round(4).to_string(index=False))

# Pre-registered criteria.
c = next((x for x in comp if x["variant"] == "bagged5"), None)
print("\nCRITERIA")
if c and c.get("per_season"):
    ok1 = c["verdict"] != "worse" and c["pooled_diff"] >= 0
    print(f"(1) points: verdict {c['verdict']}, pooled {c['pooled_diff']:+.1f} "
          f"[{c['pooled_ci'][0]:+.0f}, {c['pooled_ci'][1]:+.0f}] -> {'PASS' if ok1 else 'FAIL'}")
    ok2 = True
    for s in seasons:
        p = df[(df.season == s) & (df.variant == "production")].iloc[0]
        b = df[(df.season == s) & (df.variant == "bagged5")].iloc[0]
        good = (b.mae <= p.mae + 0.002) and (b.brier60 <= p.brier60 + 0.0005)
        ok2 &= good
        print(f"(2) {s}: MAE {p.mae:.4f} -> {b.mae:.4f}, Brier {p.brier60:.4f} -> {b.brier60:.4f} -> {'ok' if good else 'WORSE'}")
    print(f"(2) accuracy -> {'PASS' if ok2 else 'FAIL'}")
    ok3 = True
    for s in seasons:
        p = df[(df.season == s) & (df.variant == "production")].iloc[0]
        b = df[(df.season == s) & (df.variant == "bagged5")].iloc[0]
        ok3 &= b.xi_overlap > p.xi_overlap
        print(f"(3) {s}: XI overlap between seeds {p.xi_overlap:.3f} -> {b.xi_overlap:.3f}")
    pc = df[df.variant == "production"]; bc = df[df.variant == "bagged5"]
    pa = pc.cap_hits.sum() / pc.n_cap.sum(); ba = bc.cap_hits.sum() / bc.n_cap.sum()
    ok3 &= ba > pa
    print(f"(3) captain agreement between seeds (pooled) {pa:.3f} -> {ba:.3f}")
    print(f"(3) stability -> {'PASS' if ok3 else 'FAIL'}")
    print(f"\nACCEPT on these seasons: {ok1 and ok2 and ok3}")
