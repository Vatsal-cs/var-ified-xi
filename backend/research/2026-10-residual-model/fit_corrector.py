"""Fits the residual correctors from the walk-forward rows
(research/2026-10-projection-bias/rows_<season>_om.csv) and saves them here.

    python research/2026-10-residual-model/fit_corrector.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import pandas as pd
import xgboost as xgb

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = os.path.join(HERE, "..", "2026-10-projection-bias", "rows_{}_om.csv")
INPUTS = ["pred", "now_cost", "element_type", "points_avg_5", "xgi_avg_3",
          "minutes_avg_3", "starts_avg_3", "dc_avg_5"]


def rows(seasons):
    f = pd.concat([pd.read_csv(ROWS.format(s)) for s in seasons], ignore_index=True)
    for c in INPUTS:
        if c not in f.columns:
            f[c] = 0.0
    return f


def fit(seasons):
    f = rows(seasons)
    m = xgb.XGBRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, min_child_weight=50,
                         subsample=0.8, colsample_bytree=1.0, random_state=0, n_jobs=2)
    m.fit(f[INPUTS].astype(float), (f["actual"] - f["pred"]).astype(float))
    return m


if __name__ == "__main__":
    for name, seasons in (("from_2024-25", ["2024-25"]), ("from_2025-26", ["2025-26"]),
                          ("from_both", ["2024-25", "2025-26"])):
        m = fit(seasons)
        path = os.path.join(HERE, f"corrector_{name}.json")
        m.save_model(path)
        print("saved", path)
