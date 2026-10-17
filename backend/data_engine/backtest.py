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
import contextlib
import logging
import sys
import time
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd
import xgboost as xgb

import config
from data_engine import (
    availability_data,
    evaluation,
    feature_engineering,
    historical_data,
    optimizer,
    train_model,
)
from data_engine.odds_data import ODDS_FEATURE_COLUMNS
from data_engine.other_matches import FEATURES as OTHER_MATCH_FEATURES
from data_engine.other_matches import LOAD_FEATURES as OTHER_LOAD_FEATURES
from data_engine.other_matches import FORM_ADJ_FEATURES as OTHER_FORM_ADJ_FEATURES
from data_engine.setpiece_data import SETPIECE_FEATURE_COLUMNS

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
    # Returns a Series of captain-selection values aligned to the gw rows.
    # None => captain on predicted_points (the pre-ceiling behaviour).
    captain_values: Callable[[object, pd.DataFrame], pd.Series] = None
    # A context manager held open for the WHOLE variant, data loading
    # included. Anything that changes how rows are BUILT — an optional
    # feature join, a flag read inside historical_data — has to be active
    # before load_season_frame runs, not just around fit and predict. A
    # variant that only wrapped its fit would silently race against neutral
    # columns and report a verdict on nothing. See main().
    context: Callable[[], object] = None

    def build_training_set(self, history: pd.DataFrame) -> pd.DataFrame:
        prep = self.prepare or feature_engineering.build_training_set
        return prep(history)


_BASE_FEATURES = list(config.FEATURE_COLUMNS)


class _with_features:
    """Temporarily extends config.FEATURE_COLUMNS and turns on the odds join.

    Restores whatever was there before rather than the base list: these
    nest (the variant's context is held open while its fit and predict
    enter their own), and resetting to the base on the inner exit silently
    dropped the outer one's features for everything after it.
    """
    def __init__(self, extra): self.extra = extra
    def __enter__(self):
        self._old_features = config.FEATURE_COLUMNS
        config.FEATURE_COLUMNS = _BASE_FEATURES + [c for c in self.extra if c not in _BASE_FEATURES]
        self._old_odds = config.ATTACH_ODDS
        config.ATTACH_ODDS = True
    def __exit__(self, *a):
        config.FEATURE_COLUMNS = self._old_features
        config.ATTACH_ODDS = self._old_odds


class _setpiece_ctx:
    """Turns on the set-piece join and widens the feature list.

    Held open across data loading as well as fitting — the join happens in
    historical_data while rows are built, so a fit-only wrapper would train
    on columns that were never populated.
    """
    def __enter__(self):
        self._old_features = config.FEATURE_COLUMNS
        config.FEATURE_COLUMNS = _BASE_FEATURES + [
            c for c in SETPIECE_FEATURE_COLUMNS if c not in _BASE_FEATURES
        ]
        self._old = config.ATTACH_SETPIECE
        config.ATTACH_SETPIECE = True

    def __exit__(self, *a):
        config.FEATURE_COLUMNS = self._old_features
        config.ATTACH_SETPIECE = self._old


class _team_form_ctx:
    """Team quality from recent expected goals instead of FPL's ratings.
    Held open across data loading: the columns are built with the rows."""
    def __enter__(self):
        self._old = (config.TEAM_FORM, config.FEATURE_COLUMNS)
        config.TEAM_FORM = True
        config.FEATURE_COLUMNS = config.team_form_features(_BASE_FEATURES)
    def __exit__(self, *a):
        config.TEAM_FORM, config.FEATURE_COLUMNS = self._old


class _team_form_add_ctx:
    """This season's team form (xG for/against, team_form.py) built with the
    rows and ADDED to the inputs, keeping FPL's (last-season) ratings."""
    def __enter__(self):
        self._old = (config.TEAM_FORM, config.FEATURE_COLUMNS)
        config.TEAM_FORM = True
        config.FEATURE_COLUMNS = list(config.FEATURE_COLUMNS) + [
            c for c in config.TEAM_FORM_COLUMNS if c not in config.FEATURE_COLUMNS]
    def __exit__(self, *a):
        config.TEAM_FORM, config.FEATURE_COLUMNS = self._old


# The seasons being replayed in this run, set by main() before the variants
# race, for contexts that treat the replayed season differently from the
# seasons it trains on.
_REPLAYED = ()


class _live_ratings_ctx:
    """The replayed season on last season's ratings, the seasons it trains on
    with their own — how the live model runs in 2026-27."""
    def __enter__(self):
        self._old = config.LAGGED_TEAM_RATINGS_SEASONS
        config.LAGGED_TEAM_RATINGS_SEASONS = tuple(_REPLAYED)
    def __exit__(self, *a):
        config.LAGGED_TEAM_RATINGS_SEASONS = self._old


class _lagged_ratings_ctx:
    """Past seasons rated with the season-before's FPL ratings, as live."""
    def __enter__(self):
        self._old = config.LAGGED_TEAM_RATINGS
        config.LAGGED_TEAM_RATINGS = True
    def __exit__(self, *a):
        config.LAGGED_TEAM_RATINGS = self._old


class _market_source_ctx:
    """Team form built from the goals betting odds expected before each match
    (odds_data.py) instead of the xG that happened."""
    def __enter__(self):
        self._old = (config.TEAM_FORM_SOURCE, config.ATTACH_ODDS)
        config.TEAM_FORM_SOURCE, config.ATTACH_ODDS = "odds", True
    def __exit__(self, *a):
        config.TEAM_FORM_SOURCE, config.ATTACH_ODDS = self._old


@contextlib.contextmanager
def _nested(*contexts):
    """Several variant contexts entered together, left in reverse order."""
    with contextlib.ExitStack() as stack:
        for c in contexts:
            stack.enter_context(c)
        yield


class _without_features:
    """Takes columns out of config.FEATURE_COLUMNS for the whole variant,
    restoring whatever was there before (these can nest like _with_features)."""
    def __init__(self, drop): self.drop = set(drop)
    def __enter__(self):
        self._old = config.FEATURE_COLUMNS
        config.FEATURE_COLUMNS = [c for c in self._old if c not in self.drop]
    def __exit__(self, *a):
        config.FEATURE_COLUMNS = self._old


# Shrink factors for the projection-shrink test, each fitted on OTHER seasons'
# out-of-sample projections (research/2026-10-projection-bias rows): the
# season being simulated never informs its own factor.
SHRINK_BY_SEASON = {
    "2024-25": {"k": 0.687, "k_by_pos": {1: 0.552, 2: 0.813, 3: 0.634, 4: 0.582}},   # from 2025-26
    "2025-26": {"k": 0.596, "k_by_pos": {1: 0.279, 2: 0.626, 3: 0.655, 4: 0.443}},   # from 2024-25
    "2022-23": {"k": 0.654, "k_by_pos": {1: 0.362, 2: 0.759, 3: 0.657, 4: 0.509}},   # from both
    "2023-24": {"k": 0.654, "k_by_pos": {1: 0.362, 2: 0.759, 3: 0.657, 4: 0.509}},   # from both
}


# Early-season tilt toward points per match played (research/2026-10-form-tilt):
# each season's weight fitted on the OTHER tuning season's GW<=10 rows (rows
# projected 2.5+, 3+ appearances in the last five); held-back seasons get the
# mean of the two.
FORM_TILT_BY_SEASON = {"2024-25": 0.10,   # from 2025-26
                       "2025-26": 0.17,   # from 2024-25
                       "2022-23": 0.135, "2023-24": 0.135}
FORM_TILT_LAST_GW = 10


def form_tilt(pred: pd.Series, df: pd.DataFrame, w: float, last_gw: int = FORM_TILT_LAST_GW) -> pd.Series:
    """pred + w x (points per match played over the last five - pred), for
    gameweeks up to last_gw, players with 3+ of the last 5 played and
    projected 2.5+. Everything else unchanged."""
    gw = df["target_gw"] if "target_gw" in df.columns else df["round"]
    played = df["played_avg_5"].to_numpy(dtype=float)
    form = np.where(played > 0, df["points_avg_5"].to_numpy(dtype=float) / np.maximum(played, 1e-9), 0.0)
    p = pred.to_numpy(dtype=float).copy()
    m = (gw.to_numpy() <= last_gw) & (played >= 0.6 - 1e-9) & (p >= 2.5)
    p[m] += w * (form[m] - p[m])
    return pd.Series(p, index=pred.index)


def _form_tilt_predict(bundle, df):
    pred = _bundle_predict(bundle, df)
    w = FORM_TILT_BY_SEASON.get(str(df["season"].iloc[0])) if "season" in df.columns else None
    return form_tilt(pred, df, w) if w else pred


def _shrink_predict(per_position: bool):
    """Projections with config.CONDITIONAL_SHRINK set for the season being
    predicted, read from the rows themselves."""
    def predict(bundle, df):
        cfg = SHRINK_BY_SEASON.get(str(df["season"].iloc[0])) if "season" in df.columns else None
        old = config.CONDITIONAL_SHRINK
        if cfg:
            config.CONDITIONAL_SHRINK = ({"k_by_pos": cfg["k_by_pos"]} if per_position
                                         else {"k": cfg["k"]})
        try:
            return _bundle_predict(bundle, df)
        finally:
            config.CONDITIONAL_SHRINK = old
    return predict


class _other_matches_ctx:
    """Other competitions and internationals as inputs. Held open across data
    loading: the columns are built with the rows."""
    def __init__(self, columns): self.columns = columns
    def __enter__(self):
        self._old = (config.OTHER_MATCHES, config.FEATURE_COLUMNS)
        config.OTHER_MATCHES = True
        config.FEATURE_COLUMNS = list(config.FEATURE_COLUMNS) + [
            c for c in self.columns if c not in config.FEATURE_COLUMNS]
    def __exit__(self, *a):
        config.OTHER_MATCHES, config.FEATURE_COLUMNS = self._old


class _extra_features:
    """Adds already-built columns to the model's inputs for the variant."""
    def __init__(self, columns): self.columns = columns
    def __enter__(self):
        self._old = config.FEATURE_COLUMNS
        config.FEATURE_COLUMNS = list(self._old) + [c for c in self.columns if c not in self._old]
    def __exit__(self, *a):
        config.FEATURE_COLUMNS = self._old


# The residual corrector for each simulated season, fitted on OTHER seasons'
# misses (research/2026-10-residual-model).
RESIDUAL_BY_SEASON = {"2024-25": "from_2025-26", "2025-26": "from_2024-25",
                      "2022-23": "from_both", "2023-24": "from_both"}
RESIDUAL_INPUTS = ["pred", "now_cost", "element_type", "points_avg_5", "xgi_avg_3",
                   "minutes_avg_3", "starts_avg_3", "dc_avg_5"]
_residual_models = {}


def _residual_predict(bundle, df):
    base = _bundle_predict(bundle, df)
    name = RESIDUAL_BY_SEASON.get(str(df["season"].iloc[0])) if "season" in df.columns else None
    if not name:
        return base
    if name not in _residual_models:
        m = xgb.XGBRegressor()
        m.load_model(str(config.BACKEND_ROOT / "research" / "2026-10-residual-model" / f"corrector_{name}.json"))
        _residual_models[name] = m
    X = df.reindex(columns=RESIDUAL_INPUTS).assign(pred=base.to_numpy()).fillna(0).astype(float)
    corr = _residual_models[name].predict(X)
    out = np.where(base.to_numpy() >= 0.5, np.clip(base.to_numpy() + corr, 0, None), base.to_numpy())
    return pd.Series(out, index=base.index)


class _bag_ctx:
    """Temporarily sets the seed-averaging bag size used while fitting."""
    def __init__(self, size): self.size = size
    def __enter__(self):
        self._old = config.MODEL_BAG_SIZE
        config.MODEL_BAG_SIZE = self.size
    def __exit__(self, *a):
        config.MODEL_BAG_SIZE = self._old


def _bagged_fit(size: int):
    def fit(df):
        with _bag_ctx(size):
            return train_model.train_models(df, save=False)
    return fit


def _bundle_predict(bundle, predict_df: pd.DataFrame) -> pd.Series:
    return train_model.predict_points(bundle, predict_df)["predicted_points"]


RECENCY_DECAY_UNDER_TEST = 0.7


class _recency_ctx:
    def __enter__(self):
        self._old = config.RECENCY_SEASON_DECAY
        config.RECENCY_SEASON_DECAY = RECENCY_DECAY_UNDER_TEST
    def __exit__(self, *a):
        config.RECENCY_SEASON_DECAY = self._old


def _recency_fit(df):
    with _recency_ctx():
        return train_model.train_models(df, save=False, recency_weight=True)


def _odds_recency_fit(df):
    with _with_features(ODDS_FEATURE_COLUMNS), _recency_ctx():
        return train_model.train_models(df, save=False, recency_weight=True)


def _odds_ctx(fn):
    with _with_features(ODDS_FEATURE_COLUMNS):
        return fn()


def _odds_fit(df):
    with _with_features(ODDS_FEATURE_COLUMNS):
        return train_model.train_models(df, save=False)


def _odds_predict(bundle, predict_df):
    with _with_features(ODDS_FEATURE_COLUMNS):
        return train_model.predict_points(bundle, predict_df)["predicted_points"]


def _bundle_ceiling(bundle, predict_df: pd.DataFrame) -> pd.Series:
    return train_model.predict_points(bundle, predict_df)["ceiling_points"]


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
        objective="reg:squarederror", random_state=config.MODEL_SEED, n_jobs=-1,
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
        description="shipping pipeline: 2-stage, split populations, full refit, "
                    "captain on the mean projection",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
    ),
    "live_ratings": Variant(
        name="live_ratings",
        description="Reference for research/2026-10-stale-ratings (lagged_ratings vs this: -14 "
                    "[-85, +58], not used). Production as it runs live in 2026-27: trained on earlier seasons rated "
                    "with their own FPL ratings, the replayed season rated with the season "
                    "before's (research/2026-10-stale-ratings)",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=_live_ratings_ctx,
    ),
    "lagged_ratings": Variant(
        name="lagged_ratings",
        description="production, but each past season's teams rated with the PREVIOUS "
                    "season's FPL ratings — how the live model works in 2026-27, with "
                    "no hindsight from the season being replayed",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=_lagged_ratings_ctx,
    ),
    "team_form": Variant(
        name="team_form",
        description="team quality from each team's recent expected goals for and "
                    "against (team_form.py), replacing FPL's strength ratings",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=_team_form_ctx,
    ),
    "bagged5": Variant(
        name="bagged5",
        description="production, but five copies of the model with different seeds, "
                    "projections averaged (config.MODEL_BAG_SIZE = 5)",
        fit=_bagged_fit(5),
        predict=_bundle_predict,
    ),
    "no_price": Variant(
        name="no_price",
        description="NO DETECTABLE EFFECT, every run behind (Oct 2026, 5 seeds): "
                    "-128 [-287, +30], 0 of 10 runs ahead. Production without the player's "
                    "price as an input (research/2026-10-price-feature); price stays",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=lambda: _without_features(["now_cost"]),
    ),
    "no_price_own": Variant(
        name="no_price_own",
        description="NO DETECTABLE EFFECT (Oct 2026, 5 seeds): -99 [-249, +46], 2 of 10 "
                    "runs ahead. Production without price or ownership as inputs "
                    "(research/2026-10-price-feature)",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=lambda: _without_features(["now_cost", "selected_by_percent"]),
    ),
    "other_matches": Variant(
        name="other_matches",
        description="SHIPPED (Oct 2026): +87 [+13, +159] on tuning, +43 / +11 held back. "
                    "Rest since the club's last cup/European match, the next one coming, whether "
                    "the player started it, his international load — now in production too",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=lambda: _other_matches_ctx(OTHER_LOAD_FEATURES),
    ),
    "other_matches_form": Variant(
        name="other_matches_form",
        description="NO DETECTABLE EFFECT (Oct 2026, 5 seeds): +81 [-4, +168]. other_matches "
                    "plus form in those games: appearances, goals + assists, shots, shots on "
                    "target in the 30 days before",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=lambda: _other_matches_ctx(OTHER_MATCH_FEATURES),
    ),
    "sched": Variant(
        name="sched",
        description="NO DETECTABLE EFFECT (Oct 2026, 5 seeds): +18 [-65, +99]. "
                    "Production plus the strength of each player's last five opponents "
                    "(their defence and attack), so the model can weigh form by schedule "
                    "(research/2026-10-opponent-form)",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=lambda: _extra_features(["opp_def_avg_5", "opp_att_avg_5"]),
    ),
    "form_adj": Variant(
        name="form_adj",
        description="NO DETECTABLE EFFECT (Oct 2026, 5 seeds): +11 [-45, +66]. "
                    "Production plus opponent-adjusted form: xG, xGI and points scaled by "
                    "how strong each opponent was (research/2026-10-opponent-form)",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=lambda: _extra_features(["xg_adj_avg_5", "xgi_adj_avg_3", "points_adj_avg_5"]),
    ),
    "other_form_adj": Variant(
        name="other_form_adj",
        description="NO DETECTABLE EFFECT (Oct 2026, 5 seeds): -17 [-113, +87]. "
                    "Production plus form in cup/European/international games weighted by "
                    "opponent strength (Elo) (research/2026-10-opponent-form)",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=lambda: _extra_features(OTHER_FORM_ADJ_FEATURES),
    ),
    "team_form_add": Variant(
        name="team_form_add",
        description="NO DETECTABLE EFFECT (Oct 2026, 5 seeds): -0.2 [-110, +112]. "
                    "Production plus this season's team form (recent xG for and against, "
                    "per team and per match) as extra inputs, keeping the published ratings "
                    "(research/2026-10-team-form-add)",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=_team_form_add_ctx,
    ),
    "lagged_team_form_add": Variant(
        name="lagged_team_form_add",
        description="NO DETECTABLE EFFECT (Oct 2026, 5 seeds): +6 [-118, +123]. "
                    "team_form_add, with past seasons rated by the PREVIOUS season's FPL "
                    "ratings as live; compare against lagged_ratings "
                    "(research/2026-10-lagged-team-form)",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=lambda: _nested(_lagged_ratings_ctx(), _team_form_add_ctx()),
    ),
    "lagged_market_add": Variant(
        name="lagged_market_add",
        description="NO DETECTABLE EFFECT (Oct 2026, 5 seeds): +1 [-107, +111]. "
                    "lagged_ratings plus team ratings from betting odds: each team's "
                    "recency-weighted goals expected for and against by the market before "
                    "its earlier matches (research/2026-10-market-ratings)",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=lambda: _nested(_lagged_ratings_ctx(), _team_form_add_ctx(), _market_source_ctx()),
    ),
    "residual": Variant(
        name="residual",
        description="NOT USED (Oct 2026): 2024-25 -51 [-166, +53], stopped once it couldn't pass. "
                    "Production plus a second model, trained on other seasons' misses, that "
                    "corrects each projection from price, form, chances and minutes "
                    "(research/2026-10-residual-model)",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_residual_predict,
    ),
    "form_tilt": Variant(
        name="form_tilt",
        description="production plus an early-season tilt (GW<=10) toward points per match "
                    "played over the last five, weight fitted on the other season "
                    "(research/2026-10-form-tilt)",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_form_tilt_predict,
    ),
    "shrink": Variant(
        name="shrink",
        description="NO DETECTABLE EFFECT (Oct 2026, 5 seeds): -1 [-54, +53]. Points-if-60+ "
                    "projections pulled toward the position average by one factor fitted on "
                    "other seasons (research/2026-10-projection-shrink)",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_shrink_predict(per_position=False),
    ),
    "shrink_pos": Variant(
        name="shrink_pos",
        description="NO DETECTABLE EFFECT (Oct 2026, 5 seeds): -21 [-78, +40]. As shrink, "
                    "with a separate factor per position",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_shrink_predict(per_position=True),
    ),
    "setpiece": Variant(
        name="setpiece",
        description="production plus set-piece duty (penalties/free kicks/corners) "
                    "as 1/order features, joined per gameweek",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        context=_setpiece_ctx,
    ),
    "odds": Variant(
        name="odds",
        description="NO DETECTABLE EFFECT (Oct 2026, 5 seeds): +15 [-82, +107]. "
                    "First measured on one seed as REJECTED: +4 betting-odds fixture features -32 points "
                    "(split: +20 in 2025-26, -52 in 2024-25). Re-run after "
                    "Variant.context was added and reproduced exactly, so the "
                    "original verdict stands.",
        fit=_odds_fit,
        predict=_odds_predict,
        context=lambda: _with_features(ODDS_FEATURE_COLUMNS),
    ),
    "recency": Variant(
        name="recency",
        description="REJECTED: season-level recency weighting (decay 0.7) "
                    "-58 points, lost both seasons",
        fit=_recency_fit,
        predict=_bundle_predict,
    ),
    "odds_recency": Variant(
        name="odds_recency",
        description="REJECTED: odds + recency combined, -80 points (worst)",
        fit=_odds_recency_fit,
        predict=_odds_predict,
        context=lambda: _with_features(ODDS_FEATURE_COLUMNS),
    ),
    "captain_ceiling": Variant(
        name="captain_ceiling",
        description="REJECTED: captain by an 80th-percentile \"good day\" regressor instead of the mean (-8 points; tied 2024-25, lost 2025-26)",
        fit=lambda df: train_model.train_models(df, save=False),
        predict=_bundle_predict,
        captain_values=_bundle_ceiling,
    ),
    # --- Rejected alternatives, kept so the evidence stays reproducible ---
    "legacy_filtered": Variant(
        name="legacy_filtered",
        description="UNCONFIRMED (Oct 2026): both stages trained on established "
                    "starters only. +56 [+11, +103] vs production on the tuning "
                    "seasons (5 seeds), then +18 (2022-23) and -17 (2023-24) on the "
                    "held-back seasons, failing its pre-registered confirmation. "
                    "First recorded on one seed as REJECTED (MAE 1.16 vs 1.05)",
        fit=lambda df: train_model.train_models(df, save=False, quality_filter=False),
        predict=_bundle_predict,
        prepare=_legacy_training_set,
    ),
    "no_refit": Variant(
        name="no_refit",
        description="NO DETECTABLE EFFECT (Oct 2026, 5 seeds): refit is worth +43 "
                    "[-75, +171] (legacy_filtered minus this, the only difference "
                    "between them). First measured on one seed as -127: holdout "
                    "withheld from the final fit",
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
def load_season_frame(season: str, season_index: int,
                      availability: bool = True) -> pd.DataFrame:
    """Fetches one completed season and attaches rolling-form features.

    Rolling features are computed over the WHOLE season here, which is safe
    precisely because add_rolling_features() shifts every window by one
    gameweek — a row's features only ever see strictly-earlier gameweeks.
    Slicing by round afterwards therefore leaks nothing.

    availability: attach the injury flags FPL showed before each deadline
    (availability_data), so the harness scores the model production actually
    runs — one that knows who is injured. Seasons without snapshots run
    flagless and say so.
    """
    raw = historical_data.fetch_season(season, season_index=season_index)
    if raw is None or raw.empty:
        raise SystemExit(f"Season {season} could not be loaded.")

    if config.OTHER_MATCHES:
        historical_data.attach_other_matches(raw, season, season_index)
    df = feature_engineering.add_rolling_features(raw)
    df["season"] = season
    if availability:
        coverage = availability_data.attach(df, season)
        if coverage:
            logger.info("Availability %s: %.1f%% of rows matched a pre-deadline "
                        "snapshot", season, coverage * 100)
        else:
            logger.warning("Availability %s: no snapshots, so this season runs "
                           "without injury flags", season)
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
    legacy_doubles: bool = False,
    extra_bench_weights: tuple = (),
) -> dict:
    """Walks a season gameweek by gameweek, training only on the past.

    extra_bench_weights: also pick and score a squad with each of these
    bench weights, from the SAME predictions — an optimizer setting compared
    with no model noise in between. Results land in summary["extra"].

    legacy_doubles: the old handling, which collapsed a double-gameweek
    player to ONE row before predicting — so he was projected for one match
    and scored for two. Kept only to measure what fixing it changed.
    """
    rounds = sorted(r for r in season_df["round"].unique() if r >= start_gw)
    rounds = rounds[::stride]

    per_gw, preds, p60s = [], [], []
    extra = {w: [] for w in extra_bench_weights}

    for gw in rounds:
        history = season_df[season_df["round"] < gw]
        train_df = variant.build_training_set(history)
        if prior_seasons_df is not None and not prior_seasons_df.empty:
            train_df = pd.concat([train_df, prior_seasons_df], ignore_index=True)

        if len(train_df) < 100:
            logger.debug("GW%d: only %d training rows, skipping", gw, len(train_df))
            continue

        fixtures = season_df[season_df["round"] == gw].copy()
        model = variant.fit(train_df)

        if legacy_doubles:
            gw_rows = _collapse_doubles(fixtures)
            gw_rows["predicted_points"] = variant.predict(model, gw_rows).to_numpy()
            if variant.captain_values is not None:
                gw_rows["ceiling_points"] = variant.captain_values(model, gw_rows).to_numpy()
            p60 = _p60(model, gw_rows)
        else:
            # One prediction per MATCH, then summed per player — a double
            # gameweek is two chances to score, exactly as in production
            # (feature_engineering.aggregate_horizon).
            per_fixture = frozen_form_for_doubles(fixtures)
            per_fixture["predicted_points"] = variant.predict(model, per_fixture).to_numpy()
            agg = {"predicted_points": "sum"}
            if variant.captain_values is not None:
                per_fixture["ceiling_points"] = variant.captain_values(model, per_fixture).to_numpy()
                agg["ceiling_points"] = "sum"
            p60 = _p60(model, per_fixture)
            summed = per_fixture.groupby("player_id")[list(agg)].sum()
            gw_rows = _collapse_doubles(fixtures)
            for col in agg:
                gw_rows[col] = gw_rows["player_id"].map(summed[col]).to_numpy()

        if variant.captain_values is not None:
            result = optimizer.optimize_squad(gw_rows, captain_col="ceiling_points")
        else:
            result = optimizer.optimize_squad(gw_rows, captain_col="predicted_points")
        pred_lookup = gw_rows.set_index("player_id")["predicted_points"].to_dict()
        scored = score_gameweek(result, gw_rows, pred_lookup)
        captain_col = "ceiling_points" if variant.captain_values is not None else "predicted_points"
        for w in extra_bench_weights:
            r = optimizer.optimize_squad(gw_rows, captain_col=captain_col, bench_weight=w)
            extra[w].append({"gw": gw, **score_gameweek(r, gw_rows, pred_lookup),
                             "predicted": r["total_predicted_points"],
                             "xi": sorted(int(p) for p in r["starting_ids"]),
                             "captain": int(r["captain_id"]),
                             "bench_cost": int(sum(gw_rows.set_index("player_id")["now_cost"].get(p, 0)
                                                   for p in r["bench_ids"]))})

        per_gw.append({"gw": gw, **scored, "predicted": result["total_predicted_points"],
                       "xi": sorted(int(p) for p in result["starting_ids"]),
                       "captain": int(result["captain_id"]) if result["captain_id"] is not None else None})
        preds.append(pd.DataFrame({
            "pred": gw_rows["predicted_points"].to_numpy(),
            "actual": gw_rows[config.TARGET_COL].to_numpy(),
        }))
        if p60 is not None:
            p60s.append(p60)

        logger.info(
            "  GW%-2d | scored %3d pts (predicted %5.1f) | captain %2d | %d autosub(s)",
            gw, scored["points"], result["total_predicted_points"],
            scored["captain_points"], scored["autosubs"],
        )

    summary = _summarize(per_gw, preds, p60s)
    summary["extra"] = {w: _summarize(rows, preds, p60s) for w, rows in extra.items()}
    return summary


# Columns that describe a MATCH rather than the player's form going into it.
# Shared with season_sim.
FIXTURE_CONTEXT_COLUMNS = [
    "was_home",
    "team_strength_attack",
    "team_strength_defence",
    "opp_strength_attack",
    "opp_strength_defence",
    "fixture_difficulty",
    "days_since_last_match",
    "kickoff_time",
] + list(ODDS_FEATURE_COLUMNS) + ["opp_xg_for", "opp_xg_against",
                                   "match_xg_for", "match_xg_against"] + list(OTHER_MATCH_FEATURES)


def frozen_form_for_doubles(fixtures: pd.DataFrame) -> pd.DataFrame:
    """One row per match, with a double-gameweek player's FORM taken from his
    first match row for both.

    add_rolling_features shifts by one ROW, so a player's second match in a
    double gameweek carries form that includes his first — a result nobody
    knew at the deadline. Both matches get the deadline's form here; each
    keeps its own opponent, venue and rest.
    """
    fixtures = fixtures.sort_values(["player_id", "kickoff_time"]).copy()
    second = fixtures["player_id"].duplicated()
    if not second.any():
        return fixtures
    first = fixtures.drop_duplicates("player_id").set_index("player_id")
    # Model inputs only. The match's own outcome (minutes, points) has to
    # stay on its row, or the second match is graded on the first's result.
    form_cols = [c for c in config.FEATURE_COLUMNS
                 if c in fixtures.columns and c not in FIXTURE_CONTEXT_COLUMNS]
    for col in form_cols:
        fixtures.loc[second, col] = fixtures.loc[second, "player_id"].map(first[col]).to_numpy()
    return fixtures


def _p60(model, rows: pd.DataFrame):
    """The model's P(plays 60+) per row, after production's availability
    rule, alongside whether he did. None for a variant without a minutes
    model."""
    if not isinstance(model, dict) or not ("minutes_clf" in model or "members" in model):
        return None
    proba = train_model.play_probability(model, train_model._prep_X(rows))[:, train_model.FULL]
    if "chance_of_playing" in rows.columns:
        proba = proba * rows["chance_of_playing"].fillna(100).astype(float).to_numpy() / 100.0
    if "status" in rows.columns:
        proba = np.where(rows["status"].isin(["i", "s", "u", "n"]).to_numpy(), proba * 0.1, proba)
    return pd.DataFrame({"p": proba, "y": (rows["minutes"].to_numpy() >= 60).astype(int)})


def _collapse_doubles(gw_rows: pd.DataFrame) -> pd.DataFrame:
    """Collapses double-gameweek duplicates to one row per player, summing
    the quantities that accumulate across both matches (points, minutes)
    and keeping the first row's form features. For scoring and for the
    optimizer's one-row-per-player pool — predictions are made per match
    first (see simulate_season).
    """
    if not gw_rows["player_id"].duplicated().any():
        return gw_rows

    gw_rows = gw_rows.sort_values(["player_id", "kickoff_time"])
    summed = gw_rows.groupby("player_id", as_index=False).agg(
        {config.TARGET_COL: "sum", "minutes": "sum"}
    )
    first = gw_rows.drop_duplicates("player_id").drop(
        columns=[config.TARGET_COL, "minutes"]
    )
    return first.merge(summed, on="player_id")


def _summarize(per_gw, preds, p60s=None) -> dict:
    if not per_gw:
        return {"gameweeks": 0, "total_points": 0}

    df = pd.concat(preds, ignore_index=True)

    summary = {
        "gameweeks": len(per_gw),
        "total_points": int(sum(g["points"] for g in per_gw)),
        "points_per_gw": float(np.mean([g["points"] for g in per_gw])),
        "mae": float((df["pred"] - df["actual"]).abs().mean()),
        "spearman": float(df["pred"].corr(df["actual"], method="spearman")),
        # Brier score of P(plays 60+) per match, with production's injury
        # rule applied — the cleanest single check that availability data
        # is doing its job. None for variants without a minutes model.
        "brier60": None,
        "per_gw": per_gw,
    }
    if p60s:
        p = pd.concat(p60s, ignore_index=True)
        summary["brier60"] = float(((p["p"] - p["y"]) ** 2).mean())

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
# Reference variants whose result doesn't depend on the model's seed: run
# once and reused for every seed, so they still pair with seeded variants.
SEED_FREE = {"naive_form", "hindsight"}


def run_record(variant: str, season: str, seed: int, summary: dict) -> dict:
    """One (variant, season, seed) result in evaluation.py's JSON shape."""
    return {
        "variant": variant,
        "season": season,
        "seed": seed,
        "total": summary["total_points"],
        "mae": summary.get("mae"),
        "spearman": summary.get("spearman"),
        "brier60": summary.get("brier60"),
        "per_gw": [[int(g["gw"]), int(g["points"])] for g in summary.get("per_gw", [])],
        # The XI and captain chosen each week, so how much the picks move
        # between seeds can be measured, not just the points.
        "picks": [[int(g["gw"]), g.get("xi"), g.get("captain")] for g in summary.get("per_gw", [])],
    }


def write_results(path: str, harness: str, runs: list, settings: dict) -> None:
    import json
    import subprocess
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = None
    with open(path, "w") as fh:
        json.dump({"harness": harness, "commit": commit, "settings": settings,
                   "runs": runs}, fh, indent=1)
    logger.info("Wrote %d run(s) to %s", len(runs), path)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Walk-forward FPL backtest.")
    parser.add_argument("--seasons", nargs="+", default=list(config.TUNING_SEASONS),
                        help="Completed seasons to simulate.")
    parser.add_argument("--variants", nargs="+", default=["production"],
                        choices=sorted(VARIANTS), help="Model variants to race.")
    parser.add_argument("--start-gw", type=int, default=DEFAULT_START_GW,
                        help="First gameweek to simulate.")
    parser.add_argument("--stride", type=int, default=1,
                        help="Simulate every Nth gameweek (speeds up iteration).")
    parser.add_argument("--augment", action="store_true",
                        help="Also train on seasons earlier in --seasons.")
    parser.add_argument("--prior-seasons", nargs="*", default=[],
                        help="Seasons used ONLY as extra training data for every "
                             "simulated season. Lets one season run on its own "
                             "(say, in parallel) exactly as it would after "
                             "--augment: '--seasons 2025-26 --prior-seasons 2024-25'.")
    parser.add_argument("--bag-size", type=int, default=None,
                        help="models averaged per fit (default config.MODEL_BAG_SIZE); 1 is "
                             "quicker when only the optimizer is being compared")
    parser.add_argument("--seeds", nargs="+", type=int, default=[config.MODEL_SEED],
                        help="Model seeds to run every variant under. One seed "
                             "can't tell a change from noise; use 3-5.")
    parser.add_argument("--out", help="Write per-gameweek results here as JSON, "
                                      "for data_engine.evaluation to pool.")
    parser.add_argument("--tag", default="",
                        help="Suffix for variant names in the output, to tell "
                             "harness settings apart when pooling files.")
    parser.add_argument("--no-availability", action="store_true",
                        help="Old harness: no injury flags.")
    parser.add_argument("--legacy-doubles", action="store_true",
                        help="Old harness: predict a double-gameweek player for one match.")
    parser.add_argument("--block", type=int, default=2,
                        help="Bootstrap block length for the paired intervals.")
    parser.add_argument("--bench-weights", nargs="*", type=float, default=[],
                        help="Also score squads picked with these bench weights, from "
                             "the same predictions (variant@benchW in the output).")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    if args.bag_size is not None:
        config.MODEL_BAG_SIZE = args.bag_size

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

    held_back = sorted(set(args.seasons) & set(config.CONFIRMATION_SEASONS))
    if held_back:
        logger.warning("CONFIRMATION RUN on %s. These seasons are held back from "
                       "tuning: run once per accepted change and record the result, "
                       "whatever it says.", ", ".join(held_back))

    # Fixed ids per season across the whole run, so a season keeps the same
    # synthetic player ids whether it's simulated or only trained on.
    all_seasons = list(dict.fromkeys(args.prior_seasons + args.seasons))
    index = {s: i for i, s in enumerate(all_seasons)}
    availability = not args.no_availability

    global _REPLAYED
    _REPLAYED = tuple(args.seasons)
    runs = []
    for variant_name in args.variants:
        variant = VARIANTS[variant_name]
        label = variant_name + args.tag
        # Data is rebuilt per variant, inside that variant's context, because
        # an optional feature join happens while rows are BUILT. Loading once
        # up front and flipping the flag later races the variant against
        # neutral columns — a test that reports a number and measures nothing.
        # The season CSVs are disk-cached, so the cost is a re-parse.
        with (variant.context() if variant.context else contextlib.nullcontext()):
            frames = {s: load_season_frame(s, index[s], availability=availability)
                      for s in all_seasons}

            for i, season in enumerate(args.seasons):
                train_on = list(args.prior_seasons)
                if args.augment:
                    train_on += [s for s in args.seasons[:i] if s not in train_on]
                prior = None
                if train_on:
                    prior = pd.concat(
                        [feature_engineering.build_training_set(frames[s]) for s in train_on],
                        ignore_index=True,
                    )

                seeds = args.seeds[:1] if variant_name in SEED_FREE else args.seeds
                for seed in seeds:
                    config.MODEL_SEED = seed
                    logger.info("=== %s | season %s | seed %d ===", label, season, seed)
                    started = time.time()
                    summary = simulate_season(
                        frames[season], variant,
                        prior_seasons_df=prior,
                        start_gw=args.start_gw,
                        stride=args.stride,
                        legacy_doubles=args.legacy_doubles,
                        extra_bench_weights=tuple(args.bench_weights),
                    )
                    logger.info("    %s %s seed %d: %d pts in %.0fs", label, season, seed,
                                summary["total_points"], time.time() - started)
                    if variant_name in SEED_FREE:
                        runs += [run_record(label, season, s, summary) for s in args.seeds]
                    else:
                        runs.append(run_record(label, season, seed, summary))
                        for w, s in summary.get("extra", {}).items():
                            runs.append(run_record(f"{label}@bench{w:g}", season, seed, s))
                    if args.out:
                        write_results(args.out, "backtest", runs, vars(args))

    evaluation.print_report(
        runs, reference="production" + args.tag, block=args.block,
        title="BACKTEST RESULTS — unlimited-transfer simulation (comparative yardstick)",
    )


if __name__ == "__main__":
    main(sys.argv[1:])
