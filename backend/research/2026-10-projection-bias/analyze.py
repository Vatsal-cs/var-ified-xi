"""The pre-registered bias tests (PREREGISTRATION.md) on collect.py's rows.

    python research/2026-10-projection-bias/analyze.py

Two readings of the pre-registration fixed here before any result was seen:
"top third of xgi_avg_3" is taken within the group it names (midfielders and
forwards together; defenders separately), and a defender who is in both S and
A is dropped from both, since he can't stand for either side.
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TUNING = ["2024-25", "2025-26"]
REPS = 2000
POOL_MIN = 2.5
GK, DEF, MID, FWD = 1, 2, 3, 4


def load(season: str) -> pd.DataFrame:
    path = os.path.join(HERE, f"rows_{season}.csv")
    if not os.path.exists(path):
        return None
    f = pd.read_csv(path).sort_values(["player_id", "round", "kickoff_time"])
    g = f.groupby(["player_id", "round"], sort=False)
    df = g.first()
    df["pred"] = g["pred"].sum()
    df["actual"] = g["actual"].sum()
    df["n_fix"] = g.size()
    df["played60"] = (df["minutes"] >= 60).astype(int)   # first match of the round
    df = df.reset_index()
    df["season"] = season
    df["res"] = df["actual"] - df["pred"]
    if "status" in df.columns:
        df["fit_flag"] = (df["status"] == "a") & (df["chance_of_playing"].isna()
                                                  | (df["chance_of_playing"] >= 100))
    else:   # live replay: no deadline flags recorded for past weeks
        df["fit_flag"] = True
    return df


def _clusters(df):
    keys = df["season"] + ":" + df["round"].astype(str)
    codes, uniq = pd.factorize(keys)
    return codes, len(uniq)


def boot_diff(df, mask_a, mask_b, value="res", other=None, reps=REPS, seed=0):
    """mean(value | a) - mean(value | b), or with other= the paired statistic
    mean(value | a) - mean(other | a). Bootstrap over (season, gameweek)."""
    codes, k = _clusters(df)
    rng = np.random.default_rng(seed)
    v = df[value].to_numpy(float)
    o = df[other].to_numpy(float) if other else None
    a = np.asarray(mask_a)
    b = np.asarray(mask_b) if mask_b is not None else None

    def stat(w):
        ma = (w * a).sum()
        if other:
            return (w * a * v).sum() / ma - (w * a * o).sum() / ma
        return (w * a * v).sum() / ma - (w * b * v).sum() / (w * b).sum()

    point = stat(np.ones(len(df)))
    draws = []
    for _ in range(reps):
        cnt = np.bincount(rng.integers(0, k, k), minlength=k)
        draws.append(stat(cnt[codes].astype(float)))
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    return {"value": round(float(point), 3), "ci": [round(float(lo), 3), round(float(hi), 3)],
            "n_a": int(a.sum()), "n_b": int(b.sum()) if b is not None else None}


def describe(df, mask, label):
    g = df[np.asarray(mask)]
    single60 = g[(g["n_fix"] == 1) & (g["minutes"] >= 60)]
    return {
        "group": label, "n": len(g),
        "pred": round(g["pred"].mean(), 2), "actual": round(g["actual"].mean(), 2),
        "residual": round(g["res"].mean(), 2),
        "p60_pred": round(g["p60"].mean(), 3), "p60_actual": round(g["played60"].mean(), 3),
        "if60_pred": round(single60["pts_if_60"].mean(), 2),
        "if60_actual": round(single60["actual"].mean(), 2),
    }


def t1_masks(df):
    pool = df["pred"] >= POOL_MIN
    et = df["element_type"]
    s = pool & (et == DEF) & (df["dc_avg_5"] >= 10)
    att = pool & et.isin([MID, FWD])
    deff = pool & (et == DEF)
    a = (att & (df["xgi_avg_3"] >= df.loc[att, "xgi_avg_3"].quantile(2 / 3))) | \
        (deff & (df["xgi_avg_3"] >= df.loc[deff, "xgi_avg_3"].quantile(2 / 3)))
    both = s & a
    return s & ~both, a & ~both, int(both.sum())


def t2_masks(df):
    fit = df["fit_flag"]
    b = fit & (df["prev_min_1"] == 0) & (df["prev_min_2"] >= 60) & (df["prev_min_3"] >= 60)
    c = fit & (df["prev_min_1"] >= 60) & (df["prev_min_2"] >= 60) & (df["prev_min_3"] >= 60)
    return b, c


def t3_masks(df):
    pts = df[[f"prev_pts_{k}" for k in range(1, 6)]]
    played = df[[f"prev_played_{k}" for k in range(1, 6)]].fillna(False).astype(bool)
    total = pts.sum(axis=1)
    ok = (df["pred"] >= POOL_MIN) & pts.notna().all(axis=1) & (played.sum(axis=1) >= 4) & (total >= 20)
    share = pts.max(axis=1) / total.where(total > 0)
    return ok & (share >= 0.5), ok & (share <= 0.35)


def verdict(r, threshold):
    if r["value"] >= threshold and r["ci"][0] > 0:
        return "BIAS"
    return "no bias found"


def close_calls(frames) -> list:
    """Post hoc, descriptive (not pre-registered): two players in the pool in
    the same gameweek — how often does the higher projection outscore the
    lower, by the size of the gap? Ties are left out."""
    out = []
    pairs = []
    for s in TUNING:
        d = frames[s][frames[s]["pred"] >= POOL_MIN]
        for _, g in d.groupby("round"):
            p, a = g["pred"].to_numpy(), g["actual"].to_numpy()
            i, j = np.triu_indices(len(p), 1)
            hi = np.where(p[i] > p[j], a[i], a[j])
            lo = np.where(p[i] > p[j], a[j], a[i])
            pairs.append(pd.DataFrame({"gap": np.abs(p[i] - p[j]), "hi": hi, "lo": lo}))
    x = pd.concat(pairs)
    x = x[x["hi"] != x["lo"]]
    for lo_, hi_ in ((0, 0.5), (0.5, 1), (1, 1.5), (1.5, 2), (2, 3), (3, 99)):
        m = (x["gap"] > lo_) & (x["gap"] <= hi_)
        out.append({"gap": f"{lo_}-{hi_}", "pairs": int(m.sum()),
                    "higher_wins": round(float((x.loc[m, "hi"] > x.loc[m, "lo"]).mean()), 3)})
    return out


def main():
    frames = {s: load(s) for s in TUNING + ["live"]}
    out = {}

    # T1 — 2025-26 only
    d = frames["2025-26"]
    s, a, overlap = t1_masks(d)
    r = boot_diff(d, a, s)
    out["T1"] = {**r, "overlap_dropped": overlap, "verdict": verdict(r, 0.3),
                 "groups": [describe(d, a, "A attackers"), describe(d, s, "S steady defenders")]}

    # T2 and T3 — pooled over both seasons, then per season
    both = pd.concat([frames[s] for s in TUNING], ignore_index=True)
    for name, masks, kind, thr in (("T2", t2_masks, "p60", 0.10), ("T3", t3_masks, "res", 0.3)):
        res = {}
        for label, d in [("pooled", both)] + [(s, frames[s]) for s in TUNING]:
            m1, m2 = masks(d)
            if kind == "p60":
                r = boot_diff(d, m1, None, value="played60", other="p60")
                ctrl = boot_diff(d, m2, None, value="played60", other="p60")
                res[label] = {**r, "control": ctrl}
            else:
                res[label] = boot_diff(d, m1, m2)
            res[label]["groups"] = [describe(d, m1, "test"), describe(d, m2, "control")]
        res["verdict"] = verdict(res["pooled"], thr)
        out[name] = res

    # Descriptive: by position and by xgi third, every season incl. live
    desc = {}
    for season, d in frames.items():
        if d is None:
            continue
        pool = d["pred"] >= POOL_MIN
        rows = [describe(d, pool & (d["element_type"] == et), n)
                for et, n in ((GK, "GK"), (DEF, "DEF"), (MID, "MID"), (FWD, "FWD"))]
        for grp, ets in (("MID/FWD", [MID, FWD]), ("DEF", [DEF])):
            m = pool & d["element_type"].isin(ets)
            q = d.loc[m, "xgi_avg_3"].quantile([1 / 3, 2 / 3]).to_numpy()
            for lab, mm in (("low xGI", d["xgi_avg_3"] < q[0]),
                            ("mid xGI", (d["xgi_avg_3"] >= q[0]) & (d["xgi_avg_3"] < q[1])),
                            ("top xGI", d["xgi_avg_3"] >= q[1])):
                rows.append(describe(d, m & mm, f"{grp} {lab}"))
        if season != "2024-25":
            for lab, mm in (("DEF dc<6", d["dc_avg_5"] < 6), ("DEF dc 6-10", d["dc_avg_5"].between(6, 10, inclusive="left")),
                            ("DEF dc>=10", d["dc_avg_5"] >= 10)):
                rows.append(describe(d, pool & (d["element_type"] == DEF) & mm, lab))
        if season == "live":
            s_, a_, _ = t1_masks(d)
            b_, c_ = t2_masks(d)
            h_, l_ = t3_masks(d)
            rows += [describe(d, a_, "T1 A attackers"), describe(d, s_, "T1 S steady defenders"),
                     describe(d, b_, "T2 one blank"), describe(d, c_, "T2 control"),
                     describe(d, h_, "T3 haul-heavy"), describe(d, l_, "T3 steady")]
        desc[season] = rows
    out["descriptive"] = desc
    out["close_calls"] = close_calls(frames)

    with open(os.path.join(HERE, "results.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=float)

    print("T1 attackers - steady defenders (2025-26):", out["T1"]["value"], out["T1"]["ci"],
          f"n={out['T1']['n_a']}/{out['T1']['n_b']}", "->", out["T1"]["verdict"])
    for g in out["T1"]["groups"]:
        print("    ", g)
    for name in ("T2", "T3"):
        print(f"{name} ->", out[name]["verdict"])
        for label in ["pooled"] + TUNING:
            r = out[name][label]
            extra = f"  control {r['control']['value']} {r['control']['ci']}" if "control" in r else ""
            print(f"   {label:8} {r['value']:+.3f} {r['ci']} n={r['n_a']}/{r['n_b']}{extra}")
            for g in r["groups"]:
                print("        ", g)
    print("\nClose calls (post hoc): higher projection outscores the lower, ties excluded")
    print(pd.DataFrame(out["close_calls"]).to_string(index=False))
    for season, rows in desc.items():
        print(f"\n{season}")
        print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
