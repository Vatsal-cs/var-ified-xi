"""Step 1 of research/2026-10-europe-form/PREREGISTRATION.md: does form in
European, cup and international games predict the model's misses?

    python research/2026-10-europe-form/step1_signal.py
"""
import logging, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
logging.basicConfig(level=logging.ERROR)
import numpy as np
import pandas as pd
from data_engine import backtest as B

ROWS = os.path.join(HERE, "..", "2026-10-projection-bias", "rows_{}_om.csv")
FORM = ["xm_apps_30", "xm_ga_30", "xm_shots_30", "xm_sot_30", "xm_opp_30"]
REPS = 2000


def season(name, index):
    rows = pd.read_csv(ROWS.format(name))
    frame = B.load_season_frame(name, index, availability=False)
    form = frame.groupby(["player_id", "round"], as_index=False)[FORM + ["web_name"]].first()
    m = rows.merge(form.drop(columns="web_name"), on=["player_id", "round"], how="left")
    check = rows.merge(form[["player_id", "round", "web_name"]], on=["player_id", "round"], suffixes=("", "_f"))
    assert (check["web_name"] == check["web_name_f"]).mean() > 0.99, "ids don't line up"
    m["season"] = name
    return m


def boot(d, stat):
    keys = (d["season"] + ":" + d["round"].astype(str)).to_numpy()
    codes, uniq = pd.factorize(keys)
    rng = np.random.default_rng(0)
    draws = []
    for _ in range(REPS):
        w = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))[codes].astype(float)
        draws.append(stat(d, w))
    return stat(d, np.ones(len(d))), np.percentile(draws, [2.5, 97.5])


def diff(mask_a, mask_b):
    def f(d, w):
        a, b = mask_a(d).to_numpy(), mask_b(d).to_numpy()
        return (w * a * d.res).sum() / (w * a).sum() - (w * b * d.res).sum() / (w * b).sum()
    return f


def main():
    d = pd.concat([season("2024-25", 0), season("2025-26", 1)], ignore_index=True)
    d["res"] = d["actual"] - d["pred"]
    pop = d[(d.element_type >= 3) & (d.pred >= 2.5) & (d.xm_apps_30 >= 1)].copy()
    print(f"population: {len(pop)} midfielder/forward gameweeks projected 2.5+ with a European/cup/"
          f"international game in the 30 days before")
    hot, cold = (lambda x: x.xm_ga_30 >= 1), (lambda x: x.xm_ga_30 == 0)
    for name, g in [("pooled", pop)] + [(s, pop[pop.season == s]) for s in ("2024-25", "2025-26")]:
        v, ci = boot(g, diff(hot, cold))
        h, c = g[hot(g)], g[cold(g)]
        print(f"  {name:<8} goal/assist there: n={len(h):4d} projected {h.pred.mean():.2f} scored {h.actual.mean():.2f} | "
              f"none: n={len(c):4d} projected {c.pred.mean():.2f} scored {c.actual.mean():.2f} | "
              f"difference in misses {v:+.2f} [{ci[0]:+.2f}, {ci[1]:+.2f}]")
    v, ci = boot(pop, diff(hot, cold))
    go = ci[0] > 0
    print(f"\nSTEP 1 VERDICT: {'GO to step 2' if go else 'STOP — no signal beyond what the model already knows'}")

    print("\ndescriptive — opponent strength (xm_opp_30, median split) among those with a goal or assist:")
    hp = pop[hot(pop)]
    med = hp.xm_opp_30.median()
    for lab, g in (("strong opponents", hp[hp.xm_opp_30 > med]), ("weak opponents", hp[hp.xm_opp_30 <= med])):
        print(f"  {lab:<17} n={len(g):4d} projected {g.pred.mean():.2f} scored {g.actual.mean():.2f} miss {g.res.mean():+.2f}")
    print("descriptive — shots on target there (xm_sot_30):")
    for lab, g in (("2+ on target", pop[pop.xm_sot_30 >= 2]), ("0-1 on target", pop[pop.xm_sot_30 < 2])):
        print(f"  {lab:<17} n={len(g):4d} projected {g.pred.mean():.2f} scored {g.actual.mean():.2f} miss {g.res.mean():+.2f}")


if __name__ == "__main__":
    main()
