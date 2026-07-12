"""
File: train_model.py
Path: fpl-optimizer/backend/data_engine/train_model.py

Trains an XGBoost regressor to predict a player's points for the NEXT
gameweek, using rolling-form features built in feature_engineering.py.
Also handles saving/loading the model so you don't have to retrain daily.
"""

import logging
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import xgboost as xgb

from config import FEATURE_COLUMNS, TARGET_COL, MODEL_PATH

logger = logging.getLogger(__name__)


def _prep_X(df: pd.DataFrame) -> pd.DataFrame:
    X = df.reindex(columns=FEATURE_COLUMNS, fill_value=0).copy()
    return X.apply(pd.to_numeric, errors="coerce").fillna(0)


def train_xgb_model(train_df: pd.DataFrame, save: bool = True) -> xgb.XGBRegressor:
    """Trains the points-prediction model on historical gameweek rows."""
    X = _prep_X(train_df)
    y = train_df[TARGET_COL].astype(float)

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.15, random_state=42
    )

    model = xgb.XGBRegressor(
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
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    val_pred = model.predict(X_val)
    mae = mean_absolute_error(y_val, val_pred)
    logger.info("XGBoost validation MAE: %.3f points", mae)

    if save:
        joblib.dump(model, MODEL_PATH)
        logger.info("Model saved to %s", MODEL_PATH)

    return model


def load_xgb_model() -> "xgb.XGBRegressor | None":
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return None


def predict_points(model: xgb.XGBRegressor, prediction_df: pd.DataFrame) -> pd.DataFrame:
    """Adds a 'predicted_points' column to the prediction DataFrame."""
    X = _prep_X(prediction_df)
    preds = model.predict(X)
    out = prediction_df.copy()
    out["predicted_points"] = np.clip(preds, 0, None).round(2)

    # Zero out players who are injured/suspended/unavailable
    if "chance_of_playing" in out.columns:
        low_chance = out["chance_of_playing"].fillna(100) < 25
        out.loc[low_chance, "predicted_points"] *= 0.15
    if "status" in out.columns:
        out.loc[out["status"].isin(["i", "s", "u", "n"]), "predicted_points"] *= 0.1

    return out
