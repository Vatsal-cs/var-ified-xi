"""
File: season_sim.py
Path: var-ified-xi/backend/data_engine/season_sim.py

The transfer-constrained season simulation — the half of the evidence base
backtest.py always said belonged here and never got built.

backtest.py answers "are the PREDICTIONS good?" by rebuilding a fresh squad
every gameweek with unlimited transfers. That is the right way to race model
variants, and every prediction change in this project was gated on it. But it
means the transfer planner itself has never been measured: not the free
transfer logic, not the hit rule, not the horizon decay, not the captain pick
inside a squad you're actually stuck with. Those were tuned by argument.

This harness plays a real season instead:

    * one squad, carried forward from gameweek to gameweek
    * free transfers under THAT season's rules (rules.py): the bank cap, the
      2025-26 GW16 top-up, the 2022-23 unlimited week, and a first gameweek
      that banks nothing
    * every extra transfer costs TRANSFER_HIT_COST points, deducted
    * prices move with the archive, and selling returns only half the rise
    * injury flags as FPL showed them before each deadline (availability_data)
    * autosubs and the captain/vice fallback exactly as FPL applies them

The `production` policy runs the shipping decision procedure itself
(planner.plan_week — free-transfer plan, then a hit only if the hit check
says it's worth it, armband on the top projections), so what this measures
is what the dashboard tells you to do. The other policies are older research
procedures in which the solver plans hits freely and they're taken
automatically; they're kept for comparison, not because anything ships them.

What comes out is a season score a real manager could actually have posted,
which makes it directly comparable to your own.

HOW THE COMPARISON IS KEPT HONEST

Every policy in one run sees the SAME model and the SAME predictions. The
model is trained once per gameweek and handed to all of them, so any
difference in the final score is caused by the decision rule and nothing
else. That is both much faster than re-training per policy and a cleaner
experiment than racing whole pipelines against each other.

WHAT THE PREDICTIONS ARE ALLOWED TO KNOW

Planning several gameweeks ahead needs a projection for each of them, and
that is where a season simulator usually leaks. The rule here:

    form, prices and injury news are frozen at the deadline; fixtures are not.

Each player's rolling-form features come from matches played strictly BEFORE
the gameweek being planned (via latest_form_snapshot on the history slice).
The fixture context for a future gameweek — home or away, who against, how
much rest — is taken from the calendar, because in real life the fixture list
is published months ahead. A player with no fixture in a future gameweek
simply projects zero for it, which is also how blanks really work.

Price is the model's most important feature, and it used to be read from the
FUTURE gameweek's row — so a projection for five weeks out knew the price
rises and falls in between. Every horizon week now carries the deadline
price, as it does in production. Injury flags follow production too: a doubt
applies to the next gameweek only, a hard status to all of them
(feature_engineering.limit_flags_to_next_round).

CAVEATS, STATED UP FRONT

    * Chips are not played. Wildcard, bench boost, triple captain and free
      hit are all worth real points, so the totals here sit below what a
      chip-using manager would score. Every policy is equally deprived, so
      the comparison stands; the absolute number is a floor.
    * The opening squad is built by the same optimizer for every policy, so
      they all start from an identical team and diverge only through their
      own decisions.
    * Injury flags exist only from 2024-25. Earlier seasons run without
      them, so the simulated manager reacts to a player stopping playing
      rather than to the news that he will.

USAGE

    python -m data_engine.season_sim --seasons 2024-25 2025-26
    python -m data_engine.season_sim --policies production production_no_hits
    python -m data_engine.season_sim --seeds 42 7 13 --out sim.json
    python -m data_engine.season_sim --seasons 2025-26 --stride 2   (quick)
"""

import argparse
import logging
from dataclasses import dataclass, field, replace

import pandas as pd

import config
from config import TRANSFER_HIT_COST, HORIZON_GWS, HORIZON_DECAY
from data_engine import (
    backtest,
    entry_data,
    evaluation,
    feature_engineering,
    optimizer,
    horizon_availability,
    planner,
    team_form,
    rules as season_rules,
    train_model,
    transfer_optimizer,
)

logger = logging.getLogger(__name__)

DEFAULT_START_GW = 2

# Columns that describe the MATCH rather than the player's form. These are
# taken from the future gameweek's row, because the fixture list is public
# well in advance; everything else is frozen at the deadline.
FIXTURE_COLUMNS = [c for c in backtest.FIXTURE_CONTEXT_COLUMNS if c != "kickoff_time"]

# Known at the deadline and applied to every horizon week, never read from a
# future row.
DEADLINE_COLUMNS = ["now_cost", "status", "chance_of_playing", "news"]


# ---------------------------------------------------------------------------
# Policies — the decision rules being raced
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Policy:
    """One way of deciding transfers, to be raced against the others."""
    name: str
    description: str
    free_transfer_margin: float = 0.0
    captain_col: str = "predicted_points"
    max_total_hits: int = None
    horizon: int = HORIZON_GWS
    # A hit is charged TRANSFER_HIT_COST + this. None keeps config.HIT_MARGIN.
    hit_margin: float = None
    # Tilts the objective toward players the field doesn't own. Buys rank
    # variance at the cost of expected points; 0.0 disables.
    differential_weight: float = 0.0
    # Never transfers at all. The floor: how far does the opening squad get
    # you on its own? Any policy that can't beat this is doing harm.
    frozen_squad: bool = False
    # Run the shipping decision procedure (planner.plan_week) instead of one
    # unconstrained solve. hit_margin then prices the hit CHECK.
    production: bool = False
    # Under the production procedure: take a hit when the check says it's
    # worth it, as a manager following the dashboard would.
    follow_hit_advice: bool = True
    # Value injured/suspended players' later weeks with horizon_availability
    # rather than a flat hard flag.
    horizon_availability: bool = False
    # Share of a bench player's projection the planner counts. None keeps
    # config.BENCH_WEIGHT.
    bench_weight: float = None


POLICIES = {
    "production": Policy(
        name="production",
        description="what ships: free-transfer plan, a hit only when the hit check "
                    "says so, armband on the top two projections",
        production=True,
    ),
    "production_e4": Policy(
        name="production_e4",
        description="the shipping procedure, with return dates and return curves for "
                    "injured and suspended players' later weeks (horizon_availability)",
        production=True,
        horizon_availability=True,
    ),
    "production_bench0.06": Policy(
        name="production_bench0.06",
        description="the shipping procedure, bench players counted at 6% instead of 12%",
        production=True,
        bench_weight=0.06,
    ),
    "production_bench0.03": Policy(
        name="production_bench0.03",
        description="the shipping procedure, bench players counted at 3% instead of 12%",
        production=True,
        bench_weight=0.03,
    ),
    "production_no_hits": Policy(
        name="production_no_hits",
        description="the shipping procedure, but every hit verdict ignored",
        production=True,
        follow_hit_advice=False,
    ),
    "production_hm2": Policy(
        name="production_hm2",
        description="the shipping procedure with a hit check margin of 2 (a hit must gain 6)",
        production=True,
        hit_margin=2.0,
    ),
    "production_hm6": Policy(
        name="production_hm6",
        description="the shipping procedure with a hit check margin of 6 (a hit must gain 10)",
        production=True,
        hit_margin=6.0,
    ),
    "production_hm0": Policy(
        name="production_hm0",
        description="the shipping procedure, a hit taken whenever it gains more than its 4",
        production=True,
        hit_margin=0.0,
    ),
    # --- Older research procedures: the solver plans hits in any week and
    #     they are taken automatically. Not what ships; see the docstring. ---
    "baseline": Policy(
        name="baseline",
        description="solver plans and takes hits freely (margin config.HIT_MARGIN), "
                    "captain on the mean",
    ),
    "no_transfers": Policy(
        name="no_transfers",
        description="FLOOR: keep the opening squad all season, never transfer",
        frozen_squad=True,
    ),
    "ft_margin_0.5": Policy(
        name="ft_margin_0.5",
        description="a free transfer must gain 0.5 projected points",
        free_transfer_margin=0.5,
    ),
    "ft_margin_1.0": Policy(
        name="ft_margin_1.0",
        description="a free transfer must gain 1.0 projected points",
        free_transfer_margin=1.0,
    ),
    "ft_margin_1.5": Policy(
        name="ft_margin_1.5",
        description="a free transfer must gain 1.5 projected points (~the model's own error bar)",
        free_transfer_margin=1.5,
    ),
    "ft_margin_2.0": Policy(
        name="ft_margin_2.0",
        description="a free transfer must gain 2.0 projected points",
        free_transfer_margin=2.0,
    ),
    "no_hits": Policy(
        name="no_hits",
        description="free transfers only, never take a -4",
        max_total_hits=0,
    ),

    # Hit pricing. A hit really costs 4; the margin on top is how much MORE
    # than 4 the move has to gain before it's worth the certainty of losing
    # them. The first full run had the shipping margin of 2.0 spending 228
    # points on hits and still finishing behind a policy that took none, so
    # the sweep runs upward from there.
    "hit_margin_4": Policy(
        name="hit_margin_4",
        description="a hit must gain 8 (4 cost + 4 margin)",
        hit_margin=4.0,
    ),
    "hit_margin_6": Policy(
        name="hit_margin_6",
        description="a hit must gain 10 (4 cost + 6 margin)",
        hit_margin=6.0,
    ),
    "combined": Policy(
        name="combined",
        description="best of both: free transfers must gain 1.5, hits must gain 8",
        free_transfer_margin=1.5,
        hit_margin=4.0,
    ),
    "combined_6": Policy(
        name="combined_6",
        description="free transfers must gain 1.5, hits must gain 10",
        free_transfer_margin=1.5,
        hit_margin=6.0,
    ),
    "differential_0.2": Policy(
        name="differential_0.2",
        description="mild tilt toward players the field doesn't own",
        differential_weight=0.2,
    ),
    "differential_0.5": Policy(
        name="differential_0.5",
        description="strong tilt toward players the field doesn't own",
        differential_weight=0.5,
    ),
    # Hits banned on both sides, to separate the differential idea from the
    # fact that tilting inflates objective values and so makes the fixed hit
    # margin relatively cheaper.
    "diff_0.5_nohits": Policy(
        name="diff_0.5_nohits",
        description="strong differential tilt, hits banned (isolates the tilt from hit mispricing)",
        differential_weight=0.5,
        max_total_hits=0,
    ),
    "captain_ceiling": Policy(
        name="captain_ceiling",
        description="baseline, but the armband goes to the highest CEILING not the highest mean",
        captain_col="ceiling_points",
    ),
    "horizon_3": Policy(
        name="horizon_3",
        description="baseline planning 3 gameweeks ahead instead of 6",
        horizon=3,
    ),
}


# ---------------------------------------------------------------------------
# Manager state carried across gameweeks
# ---------------------------------------------------------------------------
@dataclass
class ManagerState:
    """A squad as it actually stands, mid-season."""
    squad: list = field(default_factory=list)
    bank: int = 0
    purchase_prices: dict = field(default_factory=dict)
    # Banked going into the next gameweek, before that week's top-up rules.
    free_transfers: int = 0
    points: int = 0
    captain_points: int = 0
    hits_taken: int = 0
    transfers_made: int = 0
    # Points scored by players the field mostly didn't own, weighted by how
    # unowned they were. The rank-relevant half of a score: a haul from a
    # 70%-owned player keeps you level with everyone, a haul from a 5%-owned
    # one gains you places. Reported alongside raw points so the cost and the
    # benefit of a differential tilt are both visible.
    differential_points: float = 0.0
    per_gw: list = field(default_factory=list)

    def sell_prices(self, current_prices: dict) -> dict:
        """What each owned player would fetch today, under FPL's half-the-rise
        rule. Falls back to the purchase price when the archive has no row for
        the player this gameweek (he has left the league, say).
        """
        return {
            pid: entry_data.compute_sell_price(
                self.purchase_prices.get(pid, current_prices.get(pid, 0)),
                current_prices.get(pid, self.purchase_prices.get(pid, 0)),
            )
            for pid in self.squad
        }


# ---------------------------------------------------------------------------
# Predictions for a whole planning horizon, without leaking form
# ---------------------------------------------------------------------------
def build_horizon_predictions(bundle, history: pd.DataFrame, season_df: pd.DataFrame,
                              gw: int, horizon: int, legacy_prices: bool = False,
                              horizon_rule: bool = False) -> pd.DataFrame:
    """One row per (player, future gameweek) with an expected-points figure.

    Form comes from `history` (strictly before `gw`); the match context comes
    from the real calendar; price and injury flags are the deadline's. See
    the module docstring on what that is and isn't allowed to know.

    legacy_prices: the old, leaky behaviour — each future week's price read
    from that week's row. Kept only to measure what removing the leak did.

    horizon_rule: apply horizon_availability to injured and suspended
    players' later weeks (return dates, measured return curves) instead of
    production's flat hard flag.
    """
    snapshot = feature_engineering.latest_form_snapshot(history)
    deadline_rows = season_df[season_df["round"] == gw].drop_duplicates("player_id")
    deadline = deadline_rows.set_index("player_id")

    fixture_cols = FIXTURE_COLUMNS + (["now_cost"] if legacy_prices else [])
    form_cols = [c for c in snapshot.columns
                 if c not in fixture_cols and c not in DEADLINE_COLUMNS]
    if not legacy_prices:
        # The deadline price, for every week; a player with no row this week
        # (a blank) keeps his last known one.
        snapshot["now_cost"] = snapshot["player_id"].map(deadline["now_cost"]).fillna(
            snapshot["now_cost"])
        form_cols.append("now_cost")
    if "transfer_flow" in deadline.columns and "transfer_flow" in snapshot.columns:
        # This deadline's transfers, not last week's: the snapshot is the
        # last played row, whose flow belongs to the previous deadline.
        snapshot["transfer_flow"] = snapshot["player_id"].map(
            deadline["transfer_flow"]).fillna(0.0)
    snapshot = snapshot[form_cols]

    frames = []
    for target in range(gw, gw + horizon):
        future = season_df[season_df["round"] == target]
        if future.empty:
            continue
        keep = ["player_id"] + [c for c in fixture_cols if c in future.columns]
        if config.TEAM_FORM and "opponent_team" in future.columns:
            keep.append("opponent_team")
        fixture_rows = future[keep].copy()
        fixture_rows["fixture_kickoff"] = future["kickoff_time"].to_numpy()
        merged = fixture_rows.merge(snapshot, on="player_id", how="inner")
        if merged.empty:
            continue
        merged["target_gw"] = target
        frames.append(merged)

    if not frames:
        return pd.DataFrame()

    rows = pd.concat(frames, ignore_index=True)
    # The flags FPL showed at THIS deadline, then trimmed exactly as
    # production trims them: a doubt covers the next gameweek only.
    for col, fit in (("status", "a"), ("chance_of_playing", 100.0), ("news", "")):
        if col in deadline.columns:
            rows[col] = rows["player_id"].map(deadline[col]).fillna(fit)
    feature_engineering.limit_flags_to_next_round(rows, gw, gw_col="target_gw")
    if config.TEAM_FORM and "opponent_team" in rows.columns:
        # Team ratings as of this deadline for every horizon week. A future
        # row's own columns were computed going into THAT match, so they
        # know results from the weeks in between.
        season = history["season"].iloc[0] if "season" in history.columns and len(history) else None
        _, now = team_form.ratings(team_form.team_matches(history),
                                   team_form.SEASON_START.get(season, {}))
        team_form.apply_current(rows, now)
    if horizon_rule:
        horizon_availability.apply(rows, gw, deadline_rows["kickoff_time"].min(),
                                   gw_col="target_gw", kickoff_col="fixture_kickoff")

    scored = train_model.predict_points(bundle, rows)

    # A double gameweek is two rows for one player; their expected points add
    # up the same way their real points would. P(60+) is the first match's,
    # as in production's aggregate_horizon.
    per_gw = scored.groupby(["player_id", "target_gw"], as_index=False).agg(
        predicted_points=("predicted_points", "sum"),
        ceiling_points=("ceiling_points", "sum"),
        p_full=("p_full", "first"),
    )
    return per_gw


def _collapse_to_players(per_gw: pd.DataFrame, meta: pd.DataFrame, gw: int,
                         horizon: int) -> pd.DataFrame:
    """The one-row-per-player frame the optimizers expect, carrying both the
    immediate gameweek and the decay-weighted horizon total.
    """
    immediate = per_gw[per_gw["target_gw"] == gw].set_index("player_id")

    weights = {gw + k: HORIZON_DECAY ** k for k in range(horizon)}
    per_gw = per_gw.copy()
    per_gw["weighted"] = per_gw["predicted_points"] * per_gw["target_gw"].map(weights).fillna(0)
    horizon_points = per_gw.groupby("player_id")["weighted"].sum()

    out = meta.copy()
    out["predicted_points"] = out["player_id"].map(immediate["predicted_points"]).fillna(0.0)
    out["ceiling_points"] = out["player_id"].map(immediate["ceiling_points"]).fillna(0.0)
    out["p_full"] = out["player_id"].map(immediate["p_full"]).fillna(0.0)
    out["horizon_points"] = out["player_id"].map(horizon_points).fillna(0.0)
    return out


def _with_owned(players: pd.DataFrame, squad: list, season_df: pd.DataFrame,
                prices: dict) -> pd.DataFrame:
    """Guarantees every player you own has a row in the planner's pool.

    The archive drops a player entirely once he leaves the league, and the MILP
    can't hold — or sell — a player it has no variable for, so the squad
    constraint becomes unsatisfiable and the solve comes back Infeasible.
    Re-adding him at zero projected points lets the planner do the only sane
    thing, which is sell him.
    """
    missing = [p for p in squad if p not in set(players["player_id"])]
    if not missing:
        return players

    last = (season_df[season_df["player_id"].isin(missing)]
            .sort_values("round").groupby("player_id").tail(1)
            .set_index("player_id"))

    stubs = pd.DataFrame({
        "player_id": missing,
        "web_name": [last["web_name"].get(p, str(p)) for p in missing],
        "element_type": [last["element_type"].get(p, 3) for p in missing],
        "team": [last["team"].get(p, 0) for p in missing],
        "now_cost": [prices.get(p, last["now_cost"].get(p, 0)) for p in missing],
        "predicted_points": 0.0,
        "ceiling_points": 0.0,
        "p_full": 0.0,
        "horizon_points": 0.0,
        "ownership": 0.0,
    })
    return pd.concat([players, stubs], ignore_index=True)


# ---------------------------------------------------------------------------
# One gameweek, for one policy
# ---------------------------------------------------------------------------
def _open_squad(state: ManagerState, players: pd.DataFrame, prices: dict,
                policy: Policy) -> dict:
    """The opening squad: a free pick under the budget, like a real GW1 draft.

    The week a team is created banks nothing (rules.py), so the bank stays
    at zero and the next gameweek starts with one free transfer.
    """
    result = optimizer.optimize_squad(
        players, objective_col="horizon_points", captain_col=policy.captain_col
    )
    state.squad = list(result["squad_ids"])
    state.purchase_prices = {pid: prices.get(pid, 0) for pid in state.squad}
    state.bank = config.BUDGET - sum(state.purchase_prices.values())
    state.free_transfers = 0
    return result


def _best_xi(owned: pd.DataFrame, captain_col: str) -> dict:
    """The best legal XI and captain from a squad you already own.

    Small enough to settle by enumeration: one keeper, then every legal
    outfield shape, taking the top scorers in each position. No MILP needed
    and no chance of the solver wandering off.
    """
    pts = dict(zip(owned["player_id"], owned["predicted_points"]))
    cap_pts = dict(zip(owned["player_id"], owned[captain_col]))
    by_pos = {
        etype: sorted(grp["player_id"], key=lambda p: pts.get(p, 0), reverse=True)
        for etype, grp in owned.groupby("element_type")
    }

    best, best_total = None, -1.0
    gk_lo, _ = config.STARTING_XI_LIMITS[1]
    for n_def in range(*_span(2)):
        for n_mid in range(*_span(3)):
            for n_fwd in range(*_span(4)):
                if gk_lo + n_def + n_mid + n_fwd != 11:
                    continue
                picks = (by_pos.get(1, [])[:gk_lo] + by_pos.get(2, [])[:n_def]
                         + by_pos.get(3, [])[:n_mid] + by_pos.get(4, [])[:n_fwd])
                if len(picks) != 11:
                    continue
                total = sum(pts.get(p, 0) for p in picks)
                if total > best_total:
                    best, best_total = picks, total

    if best is None:                      # squad too broken to field — shouldn't happen
        best = list(owned["player_id"])[:11]

    captain_id, vice_id = planner.pick_captains(best, cap_pts)
    return {
        "starting_ids": best,
        "bench_ids": [p for p in owned["player_id"] if p not in best],
        "captain_id": captain_id,
        "vice_captain_id": vice_id,
    }


def _span(etype: int):
    lo, hi = config.STARTING_XI_LIMITS[etype]
    return lo, hi + 1


def _xp_tables(per_gw: pd.DataFrame, policy: Policy):
    xp_by_gw = {
        pid: dict(zip(grp["target_gw"], grp["predicted_points"]))
        for pid, grp in per_gw.groupby("player_id")
    }
    captain_xp_by_gw = None
    if policy.captain_col != "predicted_points":
        captain_xp_by_gw = {
            pid: dict(zip(grp["target_gw"], grp[policy.captain_col]))
            for pid, grp in per_gw.groupby("player_id")
        }
    return xp_by_gw, captain_xp_by_gw


def _plan_week(state: ManagerState, players: pd.DataFrame, per_gw: pd.DataFrame,
               gw: int, policy: Policy, prices: dict, rules,
               available: int) -> list:
    """This gameweek's decision from the squad currently held.

    Returns the week(s) to execute, in order: the free-transfer week, then —
    under the production procedure, when the hit check says so and the
    policy follows it — the extra hit-funded moves on top. The last one is
    the team that plays.
    """
    gameweeks = sorted(g for g in per_gw["target_gw"].unique() if g >= gw)[:policy.horizon]
    xp_by_gw, captain_xp_by_gw = _xp_tables(per_gw, policy)

    sell = state.sell_prices(prices)
    team_state = entry_data.TeamState(
        entry_id=0,
        name="sim",
        gameweek=gw,
        squad=list(state.squad),
        bank=state.bank,
        squad_value=sum(sell.values()),
        free_transfers=available,
        sell_prices=sell,
    )

    captains = players.set_index("player_id")[policy.captain_col].to_dict()

    if policy.production:
        decision = planner.plan_week(
            players, team_state, xp_by_gw, gameweeks,
            hit_margin=policy.hit_margin, captain_col=policy.captain_col, rules=rules,
            bench_weight=policy.bench_weight,
        )
        week = dict(decision["plan"]["immediate"])
        week["captain_id"] = decision["result"]["captain_id"]
        week["vice_captain_id"] = decision["result"]["vice_captain_id"]
        weeks = [week]
        if decision["hit_week"] is not None and policy.follow_hit_advice:
            hit_week = dict(decision["hit_week"])
            hit_week["captain_id"], hit_week["vice_captain_id"] = planner.pick_captains(
                hit_week["starting_ids"], captains)
            weeks.append(hit_week)
        return weeks

    plan = transfer_optimizer.plan_transfers(
        players, team_state, xp_by_gw, gameweeks,
        max_total_hits=policy.max_total_hits,
        free_transfer_margin=policy.free_transfer_margin,
        hit_margin=policy.hit_margin,
        captain_xp_by_gw=captain_xp_by_gw,
        differential_weight=policy.differential_weight,
        rules=rules,
        bench_weight=policy.bench_weight,
    )
    week = dict(plan["immediate"])
    # The solver's vice has no weight in its objective, so its choice is
    # arbitrary; the armband goes where production would put it.
    week["captain_id"], week["vice_captain_id"] = planner.pick_captains(
        week["starting_ids"], captains)
    return [week]


def _differential_points(starting_ids: list, captain_id, gw_rows: pd.DataFrame) -> float:
    """How much of this gameweek's score the field didn't also get.

    Each player's actual points weighted by (1 - ownership): a haul from
    someone 70% of managers own moves you barely at all, the same haul from a
    5%-owned player moves you a long way. The captain counts twice, as he
    scores twice.
    """
    if "ownership" not in gw_rows.columns:
        return 0.0
    actual = gw_rows.set_index("player_id")[config.TARGET_COL].to_dict()
    owned = gw_rows.set_index("player_id")["ownership"].to_dict()

    total = 0.0
    for pid in starting_ids:
        edge = 1.0 - float(owned.get(pid, 0.0))
        total += float(actual.get(pid, 0)) * edge
    if captain_id is not None:
        total += float(actual.get(captain_id, 0)) * (1.0 - float(owned.get(captain_id, 0.0)))
    return total


def _pad_for_squad(gw_rows: pd.DataFrame, squad: list,
                   positions: dict) -> pd.DataFrame:
    """Gives every owned player a row for this gameweek, even if he has no
    fixture.

    A squad member can be missing from the gameweek's data for entirely real
    reasons — his club blanks, or he left the league mid-season. In FPL that
    is simply zero points and an autosub, so it is modelled as a zero row
    rather than allowed to crash the scorer.
    """
    missing = [p for p in squad if p not in set(gw_rows["player_id"])]
    if not missing:
        return gw_rows

    blanks = pd.DataFrame({
        "player_id": missing,
        "element_type": [positions.get(p, 3) for p in missing],
        config.TARGET_COL: 0,
        "minutes": 0,
    })
    return pd.concat([gw_rows, blanks], ignore_index=True)


def _apply(state: ManagerState, week: dict, prices: dict) -> None:
    """Commits one set of transfers to the carried-forward squad and bank.
    Free-transfer bookkeeping is the caller's, under the season's rules."""
    sold = [p["player_id"] for p in week["transfers_out"]]
    bought = [p["player_id"] for p in week["transfers_in"]]

    sell = state.sell_prices(prices)
    state.bank += sum(sell.get(pid, 0) for pid in sold)
    state.bank -= sum(prices.get(pid, 0) for pid in bought)

    for pid in sold:
        state.purchase_prices.pop(pid, None)
    for pid in bought:
        # A player you have just bought sells for exactly what you paid.
        state.purchase_prices[pid] = prices.get(pid, 0)

    state.squad = list(week["squad_ids"])
    state.transfers_made += week["transfer_count"]
    state.hits_taken += week["hits"]


# ---------------------------------------------------------------------------
# The season loop
# ---------------------------------------------------------------------------
def _copy_state(state: ManagerState) -> ManagerState:
    """The parts of a manager's position a decision depends on."""
    return ManagerState(squad=list(state.squad), bank=state.bank,
                        purchase_prices=dict(state.purchase_prices),
                        free_transfers=state.free_transfers)


def _decision_key(policy: Policy, state: ManagerState, available: int):
    """Everything a weekly decision depends on, besides the shared gameweek
    data: the policy's settings (not its name) and the manager's position."""
    return (replace(policy, name="", description=""),
            tuple(sorted(state.squad)), state.bank, available,
            tuple(sorted(state.purchase_prices.items())))


def _same_decision(a: list, b: list) -> bool:
    x, y = a[-1], b[-1]
    return (set(x["squad_ids"]) == set(y["squad_ids"])
            and set(x["starting_ids"]) == set(y["starting_ids"])
            and x["captain_id"] == y["captain_id"]
            and x["vice_captain_id"] == y["vice_captain_id"]
            and sum(w["hits"] for w in a) == sum(w["hits"] for w in b))


def _branch_value(pre: ManagerState, weeks: list, per_gw: pd.DataFrame, gw: int,
                  season_df: pd.DataFrame, positions: dict, prices: dict,
                  horizon: int) -> int:
    """Realised points of one decision over the next `horizon` gameweeks,
    holding the squad it produces: this week as decided, later weeks with the
    best XI and armband by the projections made at this deadline. Hits are
    deducted. Two decisions from the same state, scored this way, differ only
    by what the decisions changed.
    """
    st = _copy_state(pre)
    hit_cost = 0
    for week in weeks:
        _apply(st, week, prices)
        hit_cost += week["hit_cost"]
    played = weeks[-1]
    total = -hit_cost
    for k, g in enumerate(range(gw, gw + horizon)):
        realised = season_df[season_df["round"] == g]
        if realised.empty:
            continue
        realised = backtest._collapse_doubles(realised.copy())
        proj = per_gw[per_gw["target_gw"] == g].set_index("player_id")
        if k == 0:
            result = {
                "starting_ids": played["starting_ids"],
                "bench_ids": [p for p in played["squad_ids"] if p not in played["starting_ids"]],
                "captain_id": played["captain_id"],
                "vice_captain_id": played["vice_captain_id"],
            }
        else:
            owned = pd.DataFrame({
                "player_id": st.squad,
                "element_type": [positions.get(p, 3) for p in st.squad],
                "predicted_points": [float(proj["predicted_points"].get(p, 0.0)) for p in st.squad],
            })
            result = _best_xi(owned, "predicted_points")
        bench_value = {p: float(proj["predicted_points"].get(p, 0.0)) * float(proj["p_full"].get(p, 0.0))
                       for p in st.squad}
        scored = backtest.score_gameweek(result, _pad_for_squad(realised, st.squad, positions),
                                         bench_value)
        total += scored["points"]
    return total


def simulate(season_df: pd.DataFrame, policies: list, prior_seasons_df=None,
             start_gw: int = DEFAULT_START_GW, stride: int = 1, rules=None,
             legacy_prices: bool = False, branches: list = None) -> dict:
    """Plays one season through, for every policy, off a shared model.

    branches: [(reference policy name, candidate Policy)]. Each gameweek the
    candidate decides from the reference's exact position, and both decisions
    are scored over the following horizon (_branch_value). Weeks where they
    decide the same thing contribute exactly zero, so this sees a decision
    rule's effect through far less noise than two full seasons that drift
    apart after their first different transfer.
    """
    rules = rules or season_rules.SeasonRules(max_free_transfers=config.MAX_FREE_TRANSFERS)
    branches = branches or []
    rounds = [r for r in sorted(season_df["round"].unique()) if r >= start_gw][::stride]
    states = {p.name: ManagerState() for p in policies}
    branch_log = {cand.name: [] for _, cand in branches}
    # Positions for the whole season, so a player who blanks (or leaves the
    # league) can still be placed in a formation when scoring.
    positions = dict(zip(season_df["player_id"], season_df["element_type"]))
    view_rules = sorted({p.horizon_availability for p in policies}
                        | {c.horizon_availability for _, c in branches})

    for gw in rounds:
        history = season_df[season_df["round"] < gw]
        train_df = feature_engineering.build_training_set(history)
        if prior_seasons_df is not None and not prior_seasons_df.empty:
            train_df = pd.concat([train_df, prior_seasons_df], ignore_index=True)
        if len(train_df) < 100:
            continue

        gw_rows = backtest._collapse_doubles(season_df[season_df["round"] == gw].copy())
        if gw_rows.empty:
            continue

        # Trained once, handed to every policy — same information, different
        # decisions, so the difference in score is the decision.
        bundle = train_model.train_models(train_df, save=False)
        meta_cols = ["player_id", "web_name", "element_type", "team", "now_cost"]
        if "ownership" in gw_rows.columns:
            meta_cols.append("ownership")
        meta = gw_rows[meta_cols].copy()

        # One set of predictions per availability rule in play, from the same
        # model. The rules differ only on flagged players' later weeks.
        views = {}
        for rule in view_rules:
            per_gw = build_horizon_predictions(bundle, history, season_df, gw, HORIZON_GWS,
                                               legacy_prices=legacy_prices, horizon_rule=rule)
            if per_gw.empty:
                break
            views[rule] = (per_gw, _collapse_to_players(per_gw, meta, gw, HORIZON_GWS))
        if len(views) != len(view_rules):
            continue
        prices = dict(zip(gw_rows["player_id"], gw_rows["now_cost"]))

        # Two policies in the same position with the same settings make the
        # same decision — most usefully a branch candidate deciding from the
        # reference's position while its own season hasn't diverged from it.
        decided = {}

        def decide(st, pol, avail):
            key = _decision_key(pol, st, avail)
            if key not in decided:
                v_gw, v_players = views[pol.horizon_availability]
                pool = _with_owned(v_players, st.squad, season_df, prices)
                decided[key] = _plan_week(st, pool, v_gw, gw, pol, prices, rules, avail)
            return decided[key]

        line = [f"GW{gw:<2d}"]
        for policy in policies:
            state = states[policy.name]
            per_gw, players = views[policy.horizon_availability]

            hit_cost = 0
            if not state.squad:
                result = _open_squad(state, players, prices, policy)
                available, used_free = 0, 0
            elif policy.frozen_squad:
                owned = players[players["player_id"].isin(state.squad)]
                result = _best_xi(owned, policy.captain_col)
                available, used_free = 0, 0
            else:
                available = season_rules.free_transfers_for(rules, gw, state.free_transfers)
                pre = _copy_state(state)
                weeks = decide(pre, policy, available)
                for ref_name, cand in branches:
                    if ref_name != policy.name:
                        continue
                    c_gw, _ = views[cand.horizon_availability]
                    c_weeks = decide(pre, cand, available)
                    ref_value = _branch_value(pre, weeks, per_gw, gw, season_df, positions,
                                              prices, HORIZON_GWS)
                    changed = not _same_decision(weeks, c_weeks)
                    cand_value = (_branch_value(pre, c_weeks, c_gw, gw, season_df, positions,
                                                prices, HORIZON_GWS) if changed else ref_value)
                    branch_log[cand.name].append({"gw": gw, "reference": ref_value,
                                                  "candidate": cand_value, "changed": changed})
                used_free = 0
                for week in weeks:
                    _apply(state, week, prices)
                    hit_cost += week["hit_cost"]
                    used_free += week["transfer_count"] - week["hits"]
                played = weeks[-1]
                result = {
                    "starting_ids": played["starting_ids"],
                    "bench_ids": [p for p in played["squad_ids"]
                                  if p not in played["starting_ids"]],
                    "captain_id": played["captain_id"],
                    "vice_captain_id": played["vice_captain_id"],
                }

            # Next week's transfer is earned after this one's are spent.
            state.free_transfers = season_rules.bank_after(rules, gw, available, used_free)

            # Bench order as production sets it: projection weighted by the
            # chance he plays at all (main.order_bench).
            bench_value = dict(zip(players["player_id"],
                                   players["predicted_points"] * players["p_full"]))
            scored = backtest.score_gameweek(
                result, _pad_for_squad(gw_rows, state.squad, positions), bench_value
            )
            net = scored["points"] - hit_cost

            state.points += scored["points"]
            state.captain_points += scored["captain_points"]
            state.differential_points += _differential_points(
                result["starting_ids"], result["captain_id"], gw_rows
            )
            state.per_gw.append({"gw": gw, "points": net})
            line.append(f"{policy.name}={net:>3d}")

        for cand_name, log in branch_log.items():
            if log and log[-1]["gw"] == gw and log[-1]["changed"]:
                line.append(f"branch {cand_name} {log[-1]['candidate'] - log[-1]['reference']:+d}")
        logger.info("  " + "  |  ".join(line))

    out = {
        name: {
            "points": s.points,
            "captain_points": s.captain_points,
            "differential_points": s.differential_points,
            "transfers": s.transfers_made,
            "hits": s.hits_taken,
            "hit_cost": s.hits_taken * TRANSFER_HIT_COST,
            "gameweeks": len(s.per_gw),
            "per_gw": s.per_gw,
        }
        for name, s in states.items()
    }
    return out, branch_log


def _report(results: dict, policies: list,
            title: str = "TRANSFER-CONSTRAINED SEASON SIMULATION") -> None:
    rows = []
    for policy in policies:
        r = results.get(policy.name)
        if not r or not r["gameweeks"]:
            continue
        net = r["points"] - r["hit_cost"]
        rows.append({
            "policy": policy.name,
            "net": net,
            "raw": r["points"],
            "hits": r["hits"],
            "hit_cost": -r["hit_cost"],
            "transfers": r["transfers"],
            "captain": r["captain_points"],
            "diff": round(r["differential_points"]),
            "per_gw": round(net / r["gameweeks"], 1),
            "gws": r["gameweeks"],
        })

    if not rows:
        print("No gameweeks simulated.")
        return

    df = pd.DataFrame(rows).sort_values("net", ascending=False)
    best = df.iloc[0]
    reference = df[df["policy"] == "production"]
    if reference.empty:
        reference = df[df["policy"] == "baseline"]
    ref_name = reference.iloc[0]["policy"] if len(reference) else None
    df["vs_ref"] = (df["net"] - reference.iloc[0]["net"]) if len(reference) else 0

    print()
    print("=" * 91)
    print(title)
    print("=" * 91)
    print(f"{'policy':<20}{'NET':>7}{'raw':>7}{'hits':>6}{'cost':>7}"
          f"{'trans':>7}{'capt':>7}{'diff':>7}{'pts/gw':>8}{'vs ref':>9}")
    print("-" * 91)
    for _, r in df.iterrows():
        print(f"{r['policy']:<20}{r['net']:>7}{r['raw']:>7}{r['hits']:>6}"
              f"{r['hit_cost']:>7}{r['transfers']:>7}{r['captain']:>7}"
              f"{r['diff']:>7}{r['per_gw']:>8}{r['vs_ref']:>+9}")
    print("-" * 91)
    print(f"Highest: {best['policy']} — {POLICIES[best['policy']].description}")
    if ref_name:
        print(f"'vs ref' is against {ref_name}. One seed, one season: read the pooled")
        print("multi-seed table for a verdict, not this one.")
    print()
    print("NET is what a manager would actually have scored: points with hit")
    print("costs already deducted. Chips are not played by any policy, so all")
    print("totals sit below a real chip-using season. Compare the columns, not")
    print("the absolute number.")
    print("=" * 91)


def main():
    parser = argparse.ArgumentParser(
        description="Simulate a real, transfer-constrained FPL season."
    )
    parser.add_argument("--seasons", nargs="+", default=list(config.TUNING_SEASONS))
    parser.add_argument("--policies", nargs="+",
                        default=["production", "production_no_hits", "no_transfers"],
                        help=f"any of: {', '.join(POLICIES)}")
    parser.add_argument("--start-gw", type=int, default=DEFAULT_START_GW)
    parser.add_argument("--stride", type=int, default=1,
                        help="simulate every Nth gameweek (2 or 3 for a fast look)")
    parser.add_argument("--augment", action="store_true",
                        help="also train on the seasons before each one")
    parser.add_argument("--prior-seasons", nargs="*", default=[],
                        help="seasons used only as extra training data, so one season "
                             "can run on its own exactly as it would after --augment")
    parser.add_argument("--bag-size", type=int, default=None,
                        help="models averaged per fit (default config.MODEL_BAG_SIZE); 1 is "
                             "quicker when only the optimizer is being compared")
    parser.add_argument("--seeds", nargs="+", type=int, default=[config.MODEL_SEED],
                        help="model seeds; every policy runs under each")
    parser.add_argument("--out", help="write per-gameweek results as JSON for "
                                      "data_engine.evaluation")
    parser.add_argument("--tag", default="",
                        help="suffix for policy names in the output, to tell harness "
                             "settings apart when pooling files")
    parser.add_argument("--no-availability", action="store_true",
                        help="old harness: no injury flags")
    parser.add_argument("--legacy-prices", action="store_true",
                        help="old harness: future weeks read future prices (a leak)")
    parser.add_argument("--legacy-rules", action="store_true",
                        help="today's transfer rules (bank up to 5, no top-ups) for "
                             "every season, instead of each season's own")
    parser.add_argument("--block", type=int, default=4,
                        help="bootstrap block length in gameweeks")
    parser.add_argument("--branch", nargs="*", default=[],
                        help="REFERENCE:CANDIDATE policy pairs for the paired branch "
                             "evaluation, e.g. production:production_e4")
    args = parser.parse_args()
    if args.bag_size is not None:
        config.MODEL_BAG_SIZE = args.bag_size

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("data_engine.transfer_optimizer").setLevel(logging.WARNING)
    logging.getLogger("data_engine.optimizer").setLevel(logging.WARNING)
    logging.getLogger("data_engine.planner").setLevel(logging.WARNING)
    # The per-gameweek holdout warning fires on every one of ~37 refits and
    # says nothing about the policies being raced.
    logging.getLogger("data_engine.train_model").setLevel(logging.ERROR)

    unknown = [p for p in args.policies if p not in POLICIES]
    if unknown:
        raise SystemExit(f"Unknown policies: {unknown}. Choose from: {list(POLICIES)}")
    policies = [POLICIES[p] for p in args.policies]
    branches = []
    for pair in args.branch:
        ref_name, cand_name = pair.split(":")
        if ref_name not in args.policies or cand_name not in POLICIES:
            raise SystemExit(f"--branch {pair}: the reference must be one of --policies "
                             "and the candidate a known policy")
        branches.append((ref_name, POLICIES[cand_name]))

    held_back = sorted(set(args.seasons) & set(config.CONFIRMATION_SEASONS))
    if held_back:
        logger.warning("CONFIRMATION RUN on %s. These seasons are held back from "
                       "tuning: run once per accepted change and record the result, "
                       "whatever it says.", ", ".join(held_back))

    all_seasons = list(dict.fromkeys(args.prior_seasons + args.seasons))
    index = {s: i for i, s in enumerate(all_seasons)}
    frames = {s: backtest.load_season_frame(s, index[s],
                                            availability=not args.no_availability)
              for s in all_seasons}

    runs = []
    for i, season in enumerate(args.seasons):
        logger.info("\n=== %s ===", season)
        season_df = frames[season]

        train_on = list(args.prior_seasons)
        if args.augment:
            train_on += [s for s in args.seasons[:i] if s not in train_on]
        prior = None
        if train_on:
            prior = feature_engineering.build_training_set(
                pd.concat([frames[s] for s in train_on], ignore_index=True))

        if args.legacy_rules:
            rules = None
        else:
            rules = season_rules.for_season(season)

        for seed in args.seeds:
            config.MODEL_SEED = seed
            logger.info("--- seed %d ---", seed)
            res, branch_log = simulate(season_df, policies, prior_seasons_df=prior,
                                       start_gw=args.start_gw, stride=args.stride,
                                       rules=rules, legacy_prices=args.legacy_prices,
                                       branches=branches)
            _report(res, policies, title=f"SEASON {season} · seed {seed}")
            for name, r in res.items():
                runs.append({
                    "variant": name + args.tag,
                    "season": season,
                    "seed": seed,
                    "total": r["points"] - r["hit_cost"],
                    "hits": r["hits"],
                    "transfers": r["transfers"],
                    "captain": r["captain_points"],
                    "per_gw": [[int(g["gw"]), int(g["points"])] for g in r["per_gw"]],
                })
            for (ref_name, cand), log in zip(branches, branch_log.values()):
                for side, name in (("reference", ref_name), ("candidate", cand.name)):
                    runs.append({
                        "variant": f"branch:{name}{args.tag}",
                        "season": season,
                        "seed": seed,
                        "total": int(sum(e[side] for e in log)),
                        "changed": int(sum(e["changed"] for e in log)),
                        "per_gw": [[int(e["gw"]), int(e[side])] for e in log],
                    })
            if args.out:
                backtest.write_results(args.out, "season_sim", runs, vars(args))

    reference = "production" if "production" in args.policies else args.policies[0]
    evaluation.print_report([r for r in runs if not r["variant"].startswith("branch:")],
                            reference=reference + args.tag, block=args.block,
                            title="SEASON SIMULATION — pooled over seeds")
    for ref_name, cand in branches:
        pair = [r for r in runs if r["variant"] in (f"branch:{ref_name}{args.tag}",
                                                    f"branch:{cand.name}{args.tag}")]
        changed = sum(r.get("changed", 0) for r in pair
                      if r["variant"] == f"branch:{cand.name}{args.tag}")
        evaluation.print_report(
            pair, reference=f"branch:{ref_name}{args.tag}", block=HORIZON_GWS,
            title=f"PAIRED BRANCH TEST — {cand.name} deciding from {ref_name}'s position "
                  f"({changed} gameweek decisions differed)")


if __name__ == "__main__":
    main()
