"""
File: backtest.py
Path: var-ified-xi/backend/data_engine/backtest.py

Walk-forward season simulator — the harness that decides whether a model
change is actually an improvement or just a nicer-sounding idea.

For each gameweek t in a completed season:
    1. Train on every row from BEFORE gameweek t (plus any prior seasons).
    2. Predict gameweek t.
    3. Solve the MILP for the best squad given those predictions.
    4. Score that squad against what ACTUALLY happened in gameweek t,
       including autosubs and the captain/vice fallback.

Because step 4 uses realized points, this measures the only thing that
matters: how many points the pipeline would have scored. MAE and rank
correlation are reported alongside, but points are the verdict.

Two honest caveats about the number this prints:

  * Squads are rebuilt from scratch every gameweek (unlimited transfers).
    The absolute total is therefore far above what any real manager could
    score. It is a COMPARATIVE yardstick between model variants, not a
    prediction of your season score. The transfer-constrained simulation
    lands with the transfer planner.

  * The player pool is the vaastav archive's per-gameweek export, so
    prices/positions are as they were at the time — no hindsight there.

Two reference variants scale the result: `naive_form` (predict each player's
last-five average, no model) is the floor a model must clear to justify
existing, and `hindsight` (optimize on the actual result) is the unreachable
ceiling.

One rejected idea can't live in VARIANTS: early-season shrinkage
(FORM_SHRINKAGE_GAMES) acts while features are BUILT, before any variant
runs, so an in-list variant can't reproduce it faithfully. To re-test it,
set the knob in config.py and re-run this harness; last verdict (k=3,
gameweeks 2-38, both seasons, --augment): 4481 points vs 4545 without —
rejected. The matches_played feature already lets the model learn its own
early-season discount.

A note on a benchmark that ISN'T here. The archive carries FPL's own published
expected-points figure, and comparing against it looked like an obvious free
yardstick — until a squad built from it scored 98.7 points per gameweek across
2024-25, against ~148 for perfect hindsight and ~65-70 for a very good human.
No pre-deadline forecast reaches two thirds of hindsight; the archived values
were evidently recorded with knowledge of who actually played. It was removed
rather than left in place looking authoritative. If you want it back, it needs
values captured before the deadline, not scraped afterwards.

Usage:
    cd backend
    python -m data_engine.backtest --seasons 2024-25 2025-26
    python -m data_engine.backtest --seasons 2025-26 --variants production naive_form
    python -m data_engine.backtest --seasons 2025-26 --stride 3   # faster
"""

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd
import xgboost as xgb

import config
from data_engine import feature_engineering, historical_data, optimizer, train_model

logger = logging.getLogger(__name__)

# Simulation starts here. It used to start at gameweek 8, which quietly meant
# the opening weeks — the regime where form features rest on one or two
# matches and are least trustworthy — were never tested at all. They are now.
DEFAULT_START_GW = 2

# FPL's real bench/autosub rules, mirrored from config.STARTING_XI_LIMITS.
GK = 1


# ---------------------------------------------------------------------------
# Model variants under test
# ---------------------------------------------------------------------------
@dataclass
class Variant:
    """One pluggable pipeline to be raced against the others.

    prepare: turns the raw history of past gameweeks into a training frame.
    fit:     trains a model on that frame.
    predict: returns predicted points for a gameweek's rows.
    """
    name: str
    description: str
    fit: Callable[[pd.DataFrame], object]
    predict: Callable[[object, pd.DataFrame], pd.Series]
    prepare: Callable[[pd.DataFrame], pd.DataFrame] = None

    def build_training_set(self, history: pd.DataFrame) -> pd.DataFrame:
        prep = self.prepare or feature_engineering.build_training_set
        return prep(history)


def _bundle_predict(bundle, predict_df: pd.DataFrame) -> pd.Series:
    return train_model.predict_points(bundle, predict_df)["predicted_points"]


def _legacy_training_set(history: pd.DataFrame) -> pd.DataFrame:
    """The original training set, which dropped players with no recent minutes.

    Kept so the change that removed this filter stays measurable rather than
    becoming folklore. See feature_engineering.build_training_set.
    """
    out = history[history["minutes_avg_3"] > 0].copy()
    if "selected_by_percent" not in out.columns:
        out["selected_by_percent"] = 0.0
    return out


def _flat_fit(train_df: pd.DataFrame):
    """The pre-decomposition single regressor, as a control."""
    reg = xgb.XGBRegressor(
        n_estimators=400, max_depth=4, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8, reg_lambda=1.5,
        objective="reg:squarederror", random_state=42, n_jobs=-1,
    )
    reg.fit(train_model._prep_X(train_df), train_df[config.TARGET_COL].astype(float))
    return reg


def _flat_predict(reg, predict_df: pd.DataFrame) -> pd.Series:
    preds = np.clip(reg.predict(train_model._prep_X(predict_df)), 0, None)
    return pd.Series(preds, index=predict_df.index)


VARIANTS = {
    # What actually ships. Every other variant exists to be beaten by it, or
    # to prove it should be replaced.
    "production": Variant(
        name="production",
        description="shipping pipeline: 2-stage, split training populations, full refit",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
    ),
    # --- Rejected alternatives, kept so the evidence stays reproducible ---
    "legacy_filtered": Variant(
        name="legacy_filtered",
        description="REJECTED: both stages trained on established starters only "
                    "(over-predicts; MAE 1.16 vs 1.05)",
        fit=lambda df: train_model.train_models(df, save=False, quality_filter=False),
        predict=_bundle_predict,
        prepare=_legacy_training_set,
    ),
    "no_refit": Variant(
        name="no_refit",
        description="REJECTED: holdout withheld from the final fit (-127 points)",
        fit=lambda df: train_model.train_models(df, save=False, refit_full=False),
        predict=_bundle_predict,
        prepare=_legacy_training_set,
    ),
    "flat": Variant(
        name="flat",
        description="REJECTED: single regressor, no minutes/quality split (-53 points)",
        fit=_flat_fit,
        predict=_flat_predict,
        prepare=_legacy_training_set,
    ),
    "per_position": Variant(
        name="per_position",
        description="REJECTED: separate stage-2 regressor per position (-104 points); "
                    "splits our feature set too thin, unlike OpenFPL's larger one",
        fit=lambda df: train_model.train_models(df, save=False, per_position=True),
        predict=_bundle_predict,
    ),
    # --- Reference points, not candidates ---
    "naive_form": Variant(
        name="naive_form",
        description="FLOOR: no model at all, just each player's last-5 average",
        fit=lambda df: None,
        predict=lambda _, df: df["points_avg_5"],
    ),
    "hindsight": Variant(
        name="hindsight",
        description="CEILING: optimizes on what actually happened — unreachable "
                    "by definition, included to scale the other numbers",
        fit=lambda df: None,
        predict=lambda _, df: df[config.TARGET_COL],
    ),
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_season_frame(season: str, season_index: int) -> pd.DataFrame:
    """Fetches one completed season and attaches rolling-form features.

    Rolling features are computed over the WHOLE season here, which is safe
    precisely because add_rolling_features() shifts every window by one
    gameweek — a row's features only ever see strictly-earlier gameweeks.
    Slicing by round afterwards therefore leaks nothing.
    """
    raw = historical_data.fetch_season(season, season_index=season_index)
    if raw is None or raw.empty:
        raise SystemExit(f"Season {season} could not be loaded.")

    df = feature_engineering.add_rolling_features(raw)
    df["season"] = season
    return df


# ---------------------------------------------------------------------------
# Scoring a chosen squad against what actually happened
# ---------------------------------------------------------------------------
def _order_bench(bench_ids, pred_lookup, pos_lookup):
    """Bench order for autosubs: outfielders by predicted points descending,
    with the reserve keeper kept separate (a GK can only ever replace a GK).
    """
    outfield = [p for p in bench_ids if pos_lookup[p] != GK]
    keepers = [p for p in bench_ids if pos_lookup[p] == GK]
    outfield.sort(key=lambda p: pred_lookup.get(p, 0), reverse=True)
    return outfield, keepers


def _formation_ok(counts: dict) -> bool:
    for etype, (lo, hi) in config.STARTING_XI_LIMITS.items():
        if not lo <= counts.get(etype, 0) <= hi:
            return False
    return True


def apply_autosubs(starting_ids, bench_ids, minutes, pred_lookup, pos_lookup):
    """Replays FPL's automatic-substitution rule.

    Any starter who recorded zero minutes is replaced by the first bench
    player (in bench order) who did play, provided the resulting formation
    is still legal. Returns the list of player_ids that actually scored.
    """
    xi = list(starting_ids)
    outfield, keepers = _order_bench(bench_ids, pred_lookup, pos_lookup)

    blanks = [p for p in xi if minutes.get(p, 0) == 0]
    for out_id in blanks:
        pool = keepers if pos_lookup[out_id] == GK else outfield
        for cand in list(pool):
            if minutes.get(cand, 0) == 0:
                continue
            counts = {}
            for p in xi:
                if p == out_id:
                    continue
                counts[pos_lookup[p]] = counts.get(pos_lookup[p], 0) + 1
            counts[pos_lookup[cand]] = counts.get(pos_lookup[cand], 0) + 1
            if _formation_ok(counts):
                xi[xi.index(out_id)] = cand
                pool.remove(cand)
                break

    return xi


def score_gameweek(result: dict, gw_rows: pd.DataFrame, pred_lookup: dict) -> dict:
    """Scores one solved squad against the gameweek's realized results."""
    actual = gw_rows.set_index("player_id")[config.TARGET_COL].to_dict()
    minutes = gw_rows.set_index("player_id")["minutes"].to_dict()
    pos_lookup = gw_rows.set_index("player_id")["element_type"].to_dict()

    scoring_xi = apply_autosubs(
        result["starting_ids"], result["bench_ids"], minutes, pred_lookup, pos_lookup
    )

    base = sum(actual.get(p, 0) for p in scoring_xi)

    # Captain doubles. If the captain didn't play, the armband falls to the
    # vice-captain — exactly as FPL does it.
    captain = result["captain_id"]
    if minutes.get(captain, 0) == 0 and result.get("vice_captain_id") is not None:
        captain = result["vice_captain_id"]
    captain_bonus = actual.get(captain, 0) if captain in scoring_xi else 0

    return {
        "points": base + captain_bonus,
        "captain_points": actual.get(captain, 0),
        "autosubs": sum(1 for a, b in zip(result["starting_ids"], scoring_xi) if a != b),
    }


# ---------------------------------------------------------------------------
# The walk-forward loop
# ---------------------------------------------------------------------------
def simulate_season(
    season_df: pd.DataFrame,
    variant: Variant,
    prior_seasons_df: pd.DataFrame = None,
    start_gw: int = DEFAULT_START_GW,
    stride: int = 1,
) -> dict:
    """Walks a season gameweek by gameweek, training only on the past."""
    rounds = sorted(r for r in season_df["round"].unique() if r >= start_gw)
    rounds = rounds[::stride]

    per_gw, preds = [], []

    for gw in rounds:
        history = season_df[season_df["round"] < gw]
        train_df = variant.build_training_set(history)
        if prior_seasons_df is not None and not prior_seasons_df.empty:
            train_df = pd.concat([train_df, prior_seasons_df], ignore_index=True)

        if len(train_df) < 100:
            logger.debug("GW%d: only %d training rows, skipping", gw, len(train_df))
            continue

        gw_rows = season_df[season_df["round"] == gw].copy()
        # A player with two fixtures in one gameweek appears twice; the
        # optimizer needs one row per player, so their expected points are
        # summed the same way their real points would be.
        gw_rows = _collapse_doubles(gw_rows)

        model = variant.fit(train_df)
        gw_rows["predicted_points"] = variant.predict(model, gw_rows).to_numpy()

        result = optimizer.optimize_squad(gw_rows)
        pred_lookup = gw_rows.set_index("player_id")["predicted_points"].to_dict()
        scored = score_gameweek(result, gw_rows, pred_lookup)

        per_gw.append({"gw": gw, **scored, "predicted": result["total_predicted_points"]})
        preds.append(pd.DataFrame({
            "pred": gw_rows["predicted_points"].to_numpy(),
            "actual": gw_rows[config.TARGET_COL].to_numpy(),
        }))

        logger.info(
            "  GW%-2d | scored %3d pts (predicted %5.1f) | captain %2d | %d autosub(s)",
            gw, scored["points"], result["total_predicted_points"],
            scored["captain_points"], scored["autosubs"],
        )

    return _summarize(per_gw, preds)


def _collapse_doubles(gw_rows: pd.DataFrame) -> pd.DataFrame:
    """Collapses double-gameweek duplicates to one row per player, summing
    the quantities that accumulate across both matches (points, minutes)
    and keeping the first row's form features.
    """
    if not gw_rows["player_id"].duplicated().any():
        return gw_rows

    summed = gw_rows.groupby("player_id", as_index=False).agg(
        {config.TARGET_COL: "sum", "minutes": "sum"}
    )
    first = gw_rows.drop_duplicates("player_id").drop(
        columns=[config.TARGET_COL, "minutes"]
    )
    return first.merge(summed, on="player_id")


def _summarize(per_gw, preds) -> dict:
    if not per_gw:
        return {"gameweeks": 0, "total_points": 0}

    df = pd.concat(preds, ignore_index=True)

    summary = {
        "gameweeks": len(per_gw),
        "total_points": int(sum(g["points"] for g in per_gw)),
        "points_per_gw": float(np.mean([g["points"] for g in per_gw])),
        "mae": float((df["pred"] - df["actual"]).abs().mean()),
        "spearman": float(df["pred"].corr(df["actual"], method="spearman")),
        "per_gw": per_gw,
    }

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _print_report(results: dict) -> None:
    print()
    print("=" * 78)
    print("BACKTEST RESULTS — unlimited-transfer simulation (comparative yardstick)")
    print("=" * 78)

    header = f"{'variant':<14} {'season':<9} {'GWs':>4} {'points':>8} {'pts/GW':>7} {'MAE':>7} {'rank-r':>7}"
    print(header)
    print("-" * 78)

    for (variant, season), s in results.items():
        if not s.get("gameweeks"):
            continue
        print(
            f"{variant:<14} {season:<9} {s['gameweeks']:>4} {s['total_points']:>8} "
            f"{s['points_per_gw']:>7.1f} {s['mae']:>7.3f} {s['spearman']:>7.3f}"
        )

    print("-" * 78)
    totals = {}
    for (variant, _), s in results.items():
        if s.get("gameweeks"):
            totals.setdefault(variant, []).append(s["total_points"])
    for variant, points in totals.items():
        print(f"{variant:<14} {'ALL':<9} {'':>4} {sum(points):>8}")

    print("=" * 78)
    print("Lower MAE is better. Higher rank-r and points are better.")
    print("A change ships only if it raises points across every season tested.")
    print()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Walk-forward FPL backtest.")
    parser.add_argument("--seasons", nargs="+", default=["2024-25", "2025-26"],
                        help="Completed seasons to simulate.")
    parser.add_argument("--variants", nargs="+", default=["production"],
                        choices=sorted(VARIANTS), help="Model variants to race.")
    parser.add_argument("--start-gw", type=int, default=DEFAULT_START_GW,
                        help="First gameweek to simulate.")
    parser.add_argument("--stride", type=int, default=1,
                        help="Simulate every Nth gameweek (speeds up iteration).")
    parser.add_argument("--augment", action="store_true",
                        help="Also train on seasons earlier in --seasons.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # The per-fit validation chatter from train_model would drown the
    # gameweek log across dozens of refits.
    if not args.verbose:
        logging.getLogger("data_engine.train_model").setLevel(logging.WARNING)
        logging.getLogger("data_engine.optimizer").setLevel(logging.WARNING)
        logging.getLogger("data_engine.feature_engineering").setLevel(logging.WARNING)

    frames = {s: load_season_frame(s, i) for i, s in enumerate(args.seasons)}

    results = {}
    for variant_name in args.variants:
        variant = VARIANTS[variant_name]
        for i, season in enumerate(args.seasons):
            prior = None
            if args.augment and i > 0:
                prior = pd.concat(
                    [feature_engineering.build_training_set(frames[s])
                     for s in args.seasons[:i]],
                    ignore_index=True,
                )

            logger.info("=== %s | season %s ===", variant_name, season)
            started = time.time()
            results[(variant_name, season)] = simulate_season(
                frames[season], variant,
                prior_seasons_df=prior,
                start_gw=args.start_gw,
                stride=args.stride,
            )
            logger.info("    finished in %.0fs", time.time() - started)

    _print_report(results)


if __name__ == "__main__":
    main(sys.argv[1:])
