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

import config
from config import (
    TARGET_COL,
    MODEL_PATH,
    MIN_ROWS_PER_POSITION,
    VALIDATION_HOLDOUT_GAMEWEEKS,
    REPEAT_FLAG_THRESHOLD,
    REPEAT_FLAG_DAMPEN_FACTOR,
    CAPTAIN_QUANTILE,
)

logger = logging.getLogger(__name__)

# Minutes classes for the stage-1 classifier
DNP, CAMEO, FULL = 0, 1, 2


def _prep_X(df: pd.DataFrame) -> pd.DataFrame:
    X = df.reindex(columns=config.FEATURE_COLUMNS, fill_value=0).copy()
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
    if len(rounds) < 2:
        # Opening weeks of a season: there is no earlier gameweek to hold out
        # against, so there is no honest validation to run. Train on what
        # exists (plus past seasons) and report no accuracy figure rather
        # than inventing one.
        return train_df, train_df.iloc[0:0]
    if len(rounds) <= VALIDATION_HOLDOUT_GAMEWEEKS:
        cutoff_idx = max(1, len(rounds) - 1)
    else:
        cutoff_idx = len(rounds) - VALIDATION_HOLDOUT_GAMEWEEKS
    cutoff_round = rounds[cutoff_idx]

    return (
        train_df[train_df["round"] < cutoff_round],
        train_df[train_df["round"] >= cutoff_round],
    )


def _predict_conditional_points(bundle: dict, X: pd.DataFrame, element_types: pd.Series) -> np.ndarray:
    """E[points | played 60+], from either the pooled regressor or the
    position-specific ones when the bundle carries them.
    """
    by_pos = bundle.get("points_reg_by_pos")
    if not by_pos:
        return np.clip(bundle["points_reg"].predict(X), 0, None)

    types = np.asarray(element_types)
    out = np.zeros(len(X), dtype=float)
    for etype, reg in by_pos.items():
        mask = types == etype
        if mask.any():
            out[mask] = reg.predict(X.loc[mask])
    # Any position with too few rows to train its own regressor falls back
    # to the pooled one rather than silently scoring zero.
    unmodelled = ~np.isin(types, list(by_pos))
    if unmodelled.any():
        out[unmodelled] = bundle["points_reg"].predict(X.loc[unmodelled])
    return np.clip(out, 0, None)


def _decomposed_xp(bundle: dict, X: pd.DataFrame, element_types: pd.Series,
                   ceiling: bool = False) -> np.ndarray:
    """Combine the two stages into a single expected-points array.

    ceiling=True swaps the mean points-if-full regressor for the high-quantile
    one, giving an upside estimate used only for the captain decision.
    """
    proba = bundle["minutes_clf"].predict_proba(X)  # columns: DNP, CAMEO, FULL
    if ceiling and bundle.get("ceiling_reg") is not None:
        pts_if_full = np.clip(bundle["ceiling_reg"].predict(X), 0, None)
    else:
        pts_if_full = _predict_conditional_points(bundle, X, element_types)
    cameo_pts = element_types.map(bundle["cameo_means"]).fillna(bundle["cameo_global"]).to_numpy()
    return proba[:, FULL] * pts_if_full + proba[:, CAMEO] * cameo_pts


def _recency_weights(part: pd.DataFrame) -> "np.ndarray | None":
    """Down-weights rows from older seasons so a match from two years ago
    counts for less than one from this season, without discarding it.

    Historical player_ids are PLAYER_ID_BASE + season_index * 100_000 (see
    historical_data), season_index 0 = oldest. Current-season rows sit below
    PLAYER_ID_BASE and get full weight. Within a season every gameweek is
    weighted equally — deliberately, so this doesn't reintroduce the
    single-gameweek chasing the model was already caught doing once.
    """
    decay = config.RECENCY_SEASON_DECAY
    if decay >= 1.0:
        return None
    pid = part["player_id"].to_numpy()
    BASE = 1_000_000
    season_idx = np.where(pid >= BASE, (pid - BASE) // 100_000, -1)
    max_hist = season_idx.max()
    if max_hist < 0:
        return None
    # current season (season_idx == -1) -> exponent 0 -> weight 1
    # newest historical -> exponent 1, older -> 2, 3 ...
    exponent = np.where(season_idx < 0, 0, max_hist + 1 - season_idx)
    return decay ** exponent


def _points_regressor() -> "xgb.XGBRegressor":
    return xgb.XGBRegressor(
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


def _ceiling_regressor() -> "xgb.XGBRegressor":
    """Same shape as the mean regressor, but fit to a high quantile of
    points-given-a-start instead of the average. This is the number that
    matters for the captain pick: the armband doubles points, so what you
    want under it is the biggest realistic upside, not the steadiest return.
    """
    return xgb.XGBRegressor(
        n_estimators=400, max_depth=4, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8, reg_lambda=1.5,
        objective="reg:quantileerror", quantile_alpha=CAPTAIN_QUANTILE,
        random_state=42, n_jobs=-1,
    )


def _fit_bundle(part: pd.DataFrame, per_position: bool = False,
                quality_filter: bool = False, recency_weight: bool = False) -> dict:
    """Fits the two-stage bundle (minutes classifier + conditional points
    regressor + cameo lookup) on one partition of rows.

    per_position: fit a separate stage-2 regressor for each of GK/DEF/MID/FWD.
    The positions earn points through genuinely different mechanisms — a
    goalkeeper's return is saves and clean sheets, a forward's is goals — so
    one pooled regressor has to spend its depth budget learning to separate
    them before it can model any of them well.

    quality_filter: restrict the stage-2 regressor (but NOT the stage-1
    minutes classifier) to players with recent minutes. The two stages want
    opposite training populations. Rotation risk can only be learned from a
    sample that contains players who don't play — filter them out and the
    classifier concludes almost everyone starts, which is what makes the
    whole model over-predict. Conditional quality is the reverse: it is
    cleanest when learned from established starters.
    """
    X = _prep_X(part)
    w_all = _recency_weights(part) if recency_weight else None

    # ---- Stage 1: minutes classifier ----
    y_minutes = _minutes_class(part["minutes"])
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
    minutes_clf.fit(X, y_minutes, sample_weight=w_all, verbose=False)

    # ---- Stage 2: points regressor, trained ONLY on 60+ minute rows ----
    quality_part = part
    if quality_filter and "minutes_avg_3" in part.columns:
        filtered = part[part["minutes_avg_3"] > 0]
        # In the opening week or two of a season the rolling-form filter can
        # leave nothing behind (every average still rests on zero games).
        # Fall back to the unfiltered set rather than fitting on an empty
        # frame, which crashes the quantile regressor.
        if len(filtered) >= 200:
            quality_part = filtered

    full_rows = quality_part[quality_part["minutes"] >= 60]
    X_full = _prep_X(full_rows)
    y_full = full_rows[TARGET_COL].astype(float)

    w_full = _recency_weights(full_rows) if recency_weight else None
    points_reg = _points_regressor()
    points_reg.fit(X_full, y_full, sample_weight=w_full, verbose=False)

    # The ceiling (quantile) model is fussier about tiny/degenerate inputs;
    # only fit it when there's real data, otherwise the captain pick falls
    # back to the mean projection.
    ceiling_reg = None
    if len(full_rows) >= 300:
        ceiling_reg = _ceiling_regressor()
        ceiling_reg.fit(X_full, y_full, sample_weight=w_full, verbose=False)

    points_reg_by_pos = {}
    if per_position:
        for etype, group in full_rows.groupby("element_type"):
            if len(group) < MIN_ROWS_PER_POSITION:
                logger.debug("Position %s has only %d rows — using the pooled "
                             "regressor for it instead.", etype, len(group))
                continue
            reg = _points_regressor()
            reg.fit(_prep_X(group), group[TARGET_COL].astype(float), verbose=False)
            points_reg_by_pos[int(etype)] = reg

    # ---- Cameo value: per-position average points for 1-59 minute outings ----
    cameo_rows = quality_part[(quality_part["minutes"] > 0) & (quality_part["minutes"] < 60)]
    cameo_means = (
        cameo_rows.groupby("element_type")[TARGET_COL].mean().to_dict()
        if not cameo_rows.empty else {}
    )
    cameo_global = float(cameo_rows[TARGET_COL].mean()) if not cameo_rows.empty else 1.0

    return {
        "minutes_clf": minutes_clf,
        "points_reg": points_reg,
        "ceiling_reg": ceiling_reg,
        "points_reg_by_pos": points_reg_by_pos,
        "cameo_means": cameo_means,
        "cameo_global": cameo_global,
    }


def train_models(
    train_df: pd.DataFrame,
    historical_df: pd.DataFrame = None,
    save: bool = True,
    refit_full: bool = True,
    per_position: bool = False,
    quality_filter: bool = True,
    recency_weight: bool = False,
) -> dict:
    """Trains the two-stage model bundle (plus a flat baseline for honest
    comparison) and returns it as a dict.

    historical_df: additional rows from PAST completed seasons — concatenated
    into the TRAINING partition only, never validation.

    refit_full: after measuring accuracy on the holdout, refit the returned
    bundle on ALL rows including the holdout. Validation exists to *measure*
    the model, but the model we actually ship should learn from every
    gameweek available — especially the most recent ones, which carry the
    freshest form signal. Backtested over 2024-25 and 2025-26: +127 simulated
    points (3626 -> 3753) with better MAE and rank correlation in both
    seasons, so this is on by default. Pass False to reproduce the old
    behaviour (backtest.py's "no_refit" variant does exactly that).

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

    bundle = _fit_bundle(train_part, per_position=per_position,
                         quality_filter=quality_filter, recency_weight=recency_weight)

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
            _minutes_class(val_part["minutes"]), bundle["minutes_clf"].predict(X_val)
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

    # Accuracy has now been measured on unseen gameweeks; refit on everything
    # so the shipped model has actually seen the most recent form.
    if refit_full and not val_part.empty:
        logger.info("Refitting final bundle on all %d rows (holdout included)...",
                    len(train_part) + len(val_part))
        bundle = _fit_bundle(
            pd.concat([train_part, val_part], ignore_index=True),
            per_position=per_position,
            quality_filter=quality_filter,
            recency_weight=recency_weight,
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

    # chance_of_playing scales play probability (and therefore xP linearly)
    chance = None
    if "chance_of_playing" in out.columns:
        chance = out["chance_of_playing"].fillna(100).astype(float).to_numpy() / 100.0

    # Blank-gameweek and hard-status masks, computed once and reused for both
    # the mean projection and the captain-ceiling projection so they stay
    # consistent with each other.
    zero_mask = pd.Series(False, index=out.index)
    if "has_fixture" in out.columns and "fixtures_published" in out.columns:
        zero_mask = (~out["has_fixture"]) & out["fixtures_published"]
    elif "has_fixture" in out.columns:
        zero_mask = ~out["has_fixture"]

    status_mask = (
        out["status"].isin(["i", "s", "u", "n"]) if "status" in out.columns
        else pd.Series(False, index=out.index)
    )

    repeat_mask = pd.Series(False, index=out.index)
    if flag_counts:
        repeat_mask = out["player_id"].map(
            lambda pid: flag_counts.get(pid, 0) >= REPEAT_FLAG_THRESHOLD
        )

    def _apply(raw: np.ndarray) -> np.ndarray:
        v = np.clip(raw, 0, None)
        if chance is not None:
            v = v * chance
        v = pd.Series(v, index=out.index)
        v.loc[zero_mask] = 0.0
        v.loc[status_mask] *= 0.1
        v.loc[repeat_mask] *= REPEAT_FLAG_DAMPEN_FACTOR
        return v.round(2).to_numpy()

    out["predicted_points"] = _apply(_decomposed_xp(bundle, X, out["element_type"]))

    # Upside estimate — same pipeline, high-quantile regressor. Used only to
    # choose the captain (points doubled ⇒ you want the biggest realistic
    # score, not the safest). Falls back to the mean if the bundle predates
    # the ceiling model.
    if bundle.get("ceiling_reg") is not None:
        out["ceiling_points"] = _apply(
            _decomposed_xp(bundle, X, out["element_type"], ceiling=True)
        )
    else:
        out["ceiling_points"] = out["predicted_points"]

    return out