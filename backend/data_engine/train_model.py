"""
File: train_model.py
Path: var-ified-xi/backend/data_engine/train_model.py

v3: Two-stage "minutes x conditional points" decomposition — the structure
every serious FPL projection model uses, because rotation risk (will he
even play?) is the single biggest source of prediction error in fantasy
football, and a flat points regressor smears it together with quality.

Stage 1 — MINUTES CLASSIFIER (XGBoost multiclass):
    P(DNP), P(cameo 1-59 min), P(full 60+ min) for the upcoming match.

Stage 2 — CONDITIONAL POINTS REGRESSOR (XGBoost):
    E[points | plays 60+], trained ONLY on rows where the player actually
    played 60+ minutes — so it learns pure quality, uncontaminated by
    rotation.

Cameo appearances are valued at the observed per-position average of
1-59-minute outings (mostly the 1 appearance point plus occasional
super-sub goals) — too noisy to deserve its own regressor.

Final expected points:
    xP = P(full) * E[pts | full] + P(cameo) * cameo_avg[position]

Training also fits the OLD flat regressor on the same data and reports
both MAEs side by side on the same current-season holdout, so every run
tells you honestly whether the decomposition is actually beating the
baseline — not just assuming it does.

Validation remains a TIME-based holdout (most recent N current-season
gameweeks); historical seasons augment training only, never validation.
"""

import logging
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, accuracy_score
import xgboost as xgb

from config import (
    FEATURE_COLUMNS,
    TARGET_COL,
    MODEL_PATH,
    VALIDATION_HOLDOUT_GAMEWEEKS,
    REPEAT_FLAG_THRESHOLD,
    REPEAT_FLAG_DAMPEN_FACTOR,
)

logger = logging.getLogger(__name__)

# Minutes classes for the stage-1 classifier
DNP, CAMEO, FULL = 0, 1, 2


def _prep_X(df: pd.DataFrame) -> pd.DataFrame:
    X = df.reindex(columns=FEATURE_COLUMNS, fill_value=0).copy()
    return X.apply(pd.to_numeric, errors="coerce").fillna(0)


def _minutes_class(minutes: pd.Series) -> pd.Series:
    return pd.cut(
        minutes, bins=[-1, 0, 59, 10_000], labels=[DNP, CAMEO, FULL]
    ).astype(int)


def _temporal_split(train_df: pd.DataFrame):
    """Holds out the most recent VALIDATION_HOLDOUT_GAMEWEEKS rounds as
    validation, trains on everything earlier. This is the correct way to
    validate a time series — a random split would let the model "peek" at
    future gameweeks during training.
    """
    rounds = sorted(train_df["round"].unique())
    if len(rounds) <= VALIDATION_HOLDOUT_GAMEWEEKS:
        cutoff_idx = max(1, len(rounds) - 1)
    else:
        cutoff_idx = len(rounds) - VALIDATION_HOLDOUT_GAMEWEEKS
    cutoff_round = rounds[cutoff_idx]

    return (
        train_df[train_df["round"] < cutoff_round],
        train_df[train_df["round"] >= cutoff_round],
    )


def _decomposed_xp(bundle: dict, X: pd.DataFrame, element_types: pd.Series) -> np.ndarray:
    """Combine the two stages into a single expected-points array."""
    proba = bundle["minutes_clf"].predict_proba(X)  # columns: DNP, CAMEO, FULL
    pts_if_full = np.clip(bundle["points_reg"].predict(X), 0, None)
    cameo_pts = element_types.map(bundle["cameo_means"]).fillna(bundle["cameo_global"]).to_numpy()
    return proba[:, FULL] * pts_if_full + proba[:, CAMEO] * cameo_pts


def train_models(train_df: pd.DataFrame, historical_df: pd.DataFrame = None, save: bool = True) -> dict:
    """Trains the two-stage model bundle (plus a flat baseline for honest
    comparison) and returns it as a dict.

    historical_df: additional rows from PAST completed seasons — concatenated
    into the TRAINING partition only, never validation.

    Note on training coverage: train_df upstream filters out rows where a
    player's rolling 3-game minutes average is exactly zero (chronic
    non-players and debut rows). The classifier therefore learns the
    low-minutes boundary from low-but-nonzero form rows, where DNP is
    already the dominant class — gradient trees extrapolate sensibly for
    the true-zero region at prediction time.
    """
    train_part, val_part = _temporal_split(train_df)

    if historical_df is not None and not historical_df.empty:
        logger.info(
            "Augmenting training set with %d historical rows from past seasons "
            "(validation set unaffected — still current-season only)",
            len(historical_df),
        )
        train_part = pd.concat([train_part, historical_df], ignore_index=True)

    X_train = _prep_X(train_part)
    X_val = _prep_X(val_part)
    y_val_points = val_part[TARGET_COL].astype(float)

    # ---- Stage 1: minutes classifier ----
    y_minutes = _minutes_class(train_part["minutes"])
    minutes_clf = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )
    minutes_clf.fit(X_train, y_minutes, verbose=False)

    # ---- Stage 2: points regressor, trained ONLY on 60+ minute rows ----
    full_rows = train_part[train_part["minutes"] >= 60]
    points_reg = xgb.XGBRegressor(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.5,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1,
    )
    points_reg.fit(_prep_X(full_rows), full_rows[TARGET_COL].astype(float), verbose=False)

    # ---- Cameo value: per-position average points for 1-59 minute outings ----
    cameo_rows = train_part[(train_part["minutes"] > 0) & (train_part["minutes"] < 60)]
    cameo_means = (
        cameo_rows.groupby("element_type")[TARGET_COL].mean().to_dict()
        if not cameo_rows.empty else {}
    )
    cameo_global = float(cameo_rows[TARGET_COL].mean()) if not cameo_rows.empty else 1.0

    bundle = {
        "minutes_clf": minutes_clf,
        "points_reg": points_reg,
        "cameo_means": cameo_means,
        "cameo_global": cameo_global,
    }

    # ---- Flat baseline (the old single-regressor approach), for honest
    #      side-by-side comparison on the SAME holdout every run ----
    flat_reg = xgb.XGBRegressor(
        n_estimators=400, max_depth=4, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8, reg_lambda=1.5,
        objective="reg:squarederror", random_state=42, n_jobs=-1,
    )
    flat_reg.fit(X_train, train_part[TARGET_COL].astype(float), verbose=False)

    # ---- Validation ----
    if not val_part.empty:
        flat_mae = mean_absolute_error(y_val_points, np.clip(flat_reg.predict(X_val), 0, None))
        decomposed_val = _decomposed_xp(bundle, X_val, val_part["element_type"])
        decomposed_mae = mean_absolute_error(y_val_points, decomposed_val)
        clf_acc = accuracy_score(
            _minutes_class(val_part["minutes"]), minutes_clf.predict(X_val)
        )
        logger.info(
            "Validation (time-based holdout, last %d gameweeks, current season only):",
            VALIDATION_HOLDOUT_GAMEWEEKS,
        )
        logger.info("  Flat baseline MAE:        %.3f points", flat_mae)
        logger.info("  Decomposed (2-stage) MAE: %.3f points", decomposed_mae)
        logger.info("  Minutes classifier accuracy: %.1f%%", clf_acc * 100)
        if decomposed_mae > flat_mae:
            logger.warning(
                "Decomposed model is currently WORSE than the flat baseline on "
                "this holdout — worth investigating before trusting its picks."
            )

    if save:
        joblib.dump(bundle, MODEL_PATH)
        logger.info("Model bundle saved to %s", MODEL_PATH)

    return bundle


def load_models():
    if MODEL_PATH.exists():
        loaded = joblib.load(MODEL_PATH)
        if isinstance(loaded, dict) and "minutes_clf" in loaded:
            return loaded
        logger.warning("Saved model at %s is an old single-model format — retrain required.", MODEL_PATH)
    return None


def predict_points(bundle: dict, prediction_df: pd.DataFrame, flag_counts: dict = None) -> pd.DataFrame:
    """Adds predicted_points plus play-probability columns (p_dnp, p_cameo,
    p_full) to the prediction DataFrame.

    Availability handling: FPL's own chance_of_playing percentage now scales
    the PLAY PROBABILITY (the correct place for it in a decomposed model)
    rather than crudely multiplying final points. Hard status flags
    (injured/suspended/unavailable) still floor the prediction, and repeat
    fitness-flag history (injury_log) applies its caution multiplier on top.
    """
    X = _prep_X(prediction_df)
    out = prediction_df.copy()

    proba = bundle["minutes_clf"].predict_proba(X)
    out["p_dnp"] = proba[:, DNP].round(3)
    out["p_cameo"] = proba[:, CAMEO].round(3)
    out["p_full"] = proba[:, FULL].round(3)

    xp = _decomposed_xp(bundle, X, out["element_type"])

    # chance_of_playing scales play probability (and therefore xP linearly)
    if "chance_of_playing" in out.columns:
        chance = out["chance_of_playing"].fillna(100).astype(float) / 100.0
        xp = xp * chance.to_numpy()

    out["predicted_points"] = np.clip(xp, 0, None).round(2)

    # Zero out players with no fixture next gameweek — but ONLY when
    # fixtures are actually published league-wide (see feature_engineering).
    if "has_fixture" in out.columns and "fixtures_published" in out.columns:
        should_zero = (~out["has_fixture"]) & out["fixtures_published"]
        out.loc[should_zero, "predicted_points"] = 0.0
    elif "has_fixture" in out.columns:
        out.loc[~out["has_fixture"], "predicted_points"] = 0.0

    # Hard status flags: injured/suspended/unavailable/not-in-squad
    if "status" in out.columns:
        out.loc[out["status"].isin(["i", "s", "u", "n"]), "predicted_points"] *= 0.1

    # Extra dampening for recurring fitness-doubt history (injury_log),
    # even if today's snapshot shows the player as fully available
    if flag_counts:
        repeat_flagged = out["player_id"].map(lambda pid: flag_counts.get(pid, 0) >= REPEAT_FLAG_THRESHOLD)
        out.loc[repeat_flagged, "predicted_points"] *= REPEAT_FLAG_DAMPEN_FACTOR
        out["predicted_points"] = out["predicted_points"].round(2)

    return out