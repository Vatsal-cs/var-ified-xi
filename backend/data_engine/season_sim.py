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
    * one free transfer earned per gameweek, banked up to MAX_FREE_TRANSFERS
    * every extra transfer costs TRANSFER_HIT_COST points, deducted
    * prices move with the archive, and selling returns only half the rise
    * autosubs and the captain/vice fallback exactly as FPL applies them

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

    form is frozen at the deadline; fixtures are not.

Each player's rolling-form features come from matches played strictly BEFORE
the gameweek being planned (via latest_form_snapshot on the history slice).
The fixture context for a future gameweek — home or away, who against, how
much rest — is taken from the calendar, because in real life the fixture list
is published months ahead. A player with no fixture in a future gameweek
simply projects zero for it, which is also how blanks really work.

CAVEATS, STATED UP FRONT

    * Chips are not played. Wildcard, bench boost, triple captain and free
      hit are all worth real points, so the totals here sit below what a
      chip-using manager would score. Every policy is equally deprived, so
      the comparison stands; the absolute number is a floor.
    * The opening squad is built by the same optimizer for every policy, so
      they all start from an identical team and diverge only through their
      own decisions.
    * Injuries and suspensions are invisible in the archive beyond the
      minutes actually recorded, so the simulated manager reacts to a player
      stopping playing rather than to the news that he will.

USAGE

    python -m data_engine.season_sim --seasons 2024-25 2025-26
    python -m data_engine.season_sim --policies baseline ft_margin_1.0
    python -m data_engine.season_sim --seasons 2025-26 --stride 2   (quick)
"""

import argparse
import logging
from dataclasses import dataclass, field, replace

import pandas as pd

import config
from config import MAX_FREE_TRANSFERS, TRANSFER_HIT_COST, HORIZON_GWS, HORIZON_DECAY
from data_engine import (
    backtest,
    entry_data,
    feature_engineering,
    optimizer,
    train_model,
    transfer_optimizer,
)

logger = logging.getLogger(__name__)

DEFAULT_START_GW = 2

# Columns that describe the MATCH rather than the player's form. These are
# taken from the future gameweek's row, because the fixture list is public
# well in advance; everything else is frozen at the deadline.
FIXTURE_COLUMNS = [
    "was_home",
    "team_strength_attack",
    "team_strength_defence",
    "opp_strength_attack",
    "opp_strength_defence",
    "fixture_difficulty",
    "days_since_last_match",
    "now_cost",
]


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
    # Never transfers at all. The floor: how far does the opening squad get
    # you on its own? Any policy that can't beat this is doing harm.
    frozen_squad: bool = False


POLICIES = {
    "baseline": Policy(
        name="baseline",
        description="what ships today: free transfers cost nothing, captain on the mean",
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
    free_transfers: int = 1
    points: int = 0
    captain_points: int = 0
    hits_taken: int = 0
    transfers_made: int = 0
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
                              gw: int, horizon: int) -> pd.DataFrame:
    """One row per (player, future gameweek) with an expected-points figure.

    Form comes from `history` (strictly before `gw`); the match context comes
    from the real calendar. See the module docstring on what that is and isn't
    allowed to know.
    """
    snapshot = feature_engineering.latest_form_snapshot(history)
    form_cols = [c for c in snapshot.columns if c not in FIXTURE_COLUMNS]
    snapshot = snapshot[form_cols]

    frames = []
    for target in range(gw, gw + horizon):
        future = season_df[season_df["round"] == target]
        if future.empty:
            continue
        keep = ["player_id"] + [c for c in FIXTURE_COLUMNS if c in future.columns]
        fixture_rows = future[keep].copy()
        merged = fixture_rows.merge(snapshot, on="player_id", how="inner")
        if merged.empty:
            continue
        merged["target_gw"] = target
        frames.append(merged)

    if not frames:
        return pd.DataFrame()

    rows = pd.concat(frames, ignore_index=True)
    scored = train_model.predict_points(bundle, rows)

    # A double gameweek is two rows for one player; their expected points add
    # up the same way their real points would.
    per_gw = scored.groupby(["player_id", "target_gw"], as_index=False).agg(
        predicted_points=("predicted_points", "sum"),
        ceiling_points=("ceiling_points", "sum"),
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
        "horizon_points": 0.0,
    })
    return pd.concat([players, stubs], ignore_index=True)


# ---------------------------------------------------------------------------
# One gameweek, for one policy
# ---------------------------------------------------------------------------
def _open_squad(state: ManagerState, players: pd.DataFrame, prices: dict,
                policy: Policy) -> dict:
    """The opening squad: a free pick under the budget, like a real GW1 draft."""
    result = optimizer.optimize_squad(
        players, objective_col="horizon_points", captain_col=policy.captain_col
    )
    state.squad = list(result["squad_ids"])
    state.purchase_prices = {pid: prices.get(pid, 0) for pid in state.squad}
    state.bank = config.BUDGET - sum(state.purchase_prices.values())
    state.free_transfers = 1
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

    ranked = sorted(best, key=lambda p: cap_pts.get(p, 0), reverse=True)
    return {
        "starting_ids": best,
        "bench_ids": [p for p in owned["player_id"] if p not in best],
        "captain_id": ranked[0] if ranked else None,
        "vice_captain_id": ranked[1] if len(ranked) > 1 else None,
    }


def _span(etype: int):
    lo, hi = config.STARTING_XI_LIMITS[etype]
    return lo, hi + 1


def _plan_week(state: ManagerState, players: pd.DataFrame, per_gw: pd.DataFrame,
               gw: int, policy: Policy, prices: dict) -> dict:
    """Runs the real transfer planner from the squad currently held."""
    gameweeks = sorted(g for g in per_gw["target_gw"].unique() if g >= gw)[:policy.horizon]
    xp_by_gw = {
        pid: dict(zip(grp["target_gw"], grp["predicted_points"]))
        for pid, grp in per_gw.groupby("player_id")
    }

    sell = state.sell_prices(prices)
    team_state = entry_data.TeamState(
        entry_id=0,
        name="sim",
        gameweek=gw,
        squad=list(state.squad),
        bank=state.bank,
        squad_value=sum(sell.values()),
        free_transfers=state.free_transfers,
        sell_prices=sell,
    )

    plan = transfer_optimizer.plan_transfers(
        players, team_state, xp_by_gw, gameweeks,
        max_total_hits=policy.max_total_hits,
        free_transfer_margin=policy.free_transfer_margin,
        hit_margin=policy.hit_margin,
    )
    return plan["immediate"]


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
    """Commits this gameweek's transfers to the carried-forward state."""
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

    used = week["transfer_count"]
    hits = week["hits"]
    state.transfers_made += used
    state.hits_taken += hits
    # Free transfers spent are the ones not paid for in points.
    state.free_transfers = max(0, state.free_transfers - (used - hits))


# ---------------------------------------------------------------------------
# The season loop
# ---------------------------------------------------------------------------
def simulate(season_df: pd.DataFrame, policies: list, prior_seasons_df=None,
             start_gw: int = DEFAULT_START_GW, stride: int = 1) -> dict:
    """Plays one season through, for every policy, off a shared model."""
    rounds = [r for r in sorted(season_df["round"].unique()) if r >= start_gw][::stride]
    states = {p.name: ManagerState() for p in policies}
    # Positions for the whole season, so a player who blanks (or leaves the
    # league) can still be placed in a formation when scoring.
    positions = dict(zip(season_df["player_id"], season_df["element_type"]))

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
        per_gw = build_horizon_predictions(bundle, history, season_df, gw, HORIZON_GWS)
        if per_gw.empty:
            continue

        meta = gw_rows[["player_id", "web_name", "element_type", "team", "now_cost"]].copy()
        players = _collapse_to_players(per_gw, meta, gw, HORIZON_GWS)
        prices = dict(zip(gw_rows["player_id"], gw_rows["now_cost"]))

        line = [f"GW{gw:<2d}"]
        for policy in policies:
            state = states[policy.name]

            hit_cost = 0
            if not state.squad:
                result = _open_squad(state, players, prices, policy)
            elif policy.frozen_squad:
                owned = players[players["player_id"].isin(state.squad)]
                result = _best_xi(owned, policy.captain_col)
            else:
                pool = _with_owned(players, state.squad, season_df, prices)
                week = _plan_week(state, pool, per_gw, gw, policy, prices)
                _apply(state, week, prices)
                hit_cost = week["hit_cost"]
                result = {
                    "starting_ids": week["starting_ids"],
                    "bench_ids": [p for p in week["squad_ids"]
                                  if p not in week["starting_ids"]],
                    "captain_id": week["captain_id"],
                    "vice_captain_id": week["vice_captain_id"],
                }

            # Next week's transfer is earned after this one's are spent.
            state.free_transfers = min(state.free_transfers + 1, MAX_FREE_TRANSFERS)

            pred_lookup = dict(zip(players["player_id"], players["predicted_points"]))
            scored = backtest.score_gameweek(
                result, _pad_for_squad(gw_rows, state.squad, positions), pred_lookup
            )
            net = scored["points"] - hit_cost

            state.points += scored["points"]
            state.captain_points += scored["captain_points"]
            state.per_gw.append({"gw": gw, "points": net})
            line.append(f"{policy.name}={net:>3d}")

        logger.info("  " + "  |  ".join(line))

    return {
        name: {
            "points": s.points,
            "captain_points": s.captain_points,
            "transfers": s.transfers_made,
            "hits": s.hits_taken,
            "hit_cost": s.hits_taken * TRANSFER_HIT_COST,
            "gameweeks": len(s.per_gw),
        }
        for name, s in states.items()
    }


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
            "per_gw": round(net / r["gameweeks"], 1),
            "gws": r["gameweeks"],
        })

    if not rows:
        print("No gameweeks simulated.")
        return

    df = pd.DataFrame(rows).sort_values("net", ascending=False)
    best = df.iloc[0]
    baseline = df[df["policy"] == "baseline"]
    df["vs_base"] = (df["net"] - baseline.iloc[0]["net"]) if len(baseline) else 0

    print()
    print("=" * 84)
    print(title)
    print("=" * 84)
    print(f"{'policy':<18}{'NET':>7}{'raw':>7}{'hits':>6}{'cost':>7}"
          f"{'trans':>7}{'capt':>7}{'pts/gw':>8}{'vs base':>9}")
    print("-" * 84)
    for _, r in df.iterrows():
        print(f"{r['policy']:<18}{r['net']:>7}{r['raw']:>7}{r['hits']:>6}"
              f"{r['hit_cost']:>7}{r['transfers']:>7}{r['captain']:>7}"
              f"{r['per_gw']:>8}{r['vs_base']:>+9}")
    print("-" * 84)
    print(f"Winner: {best['policy']} — {POLICIES[best['policy']].description}")
    print()
    print("NET is what a manager would actually have scored: points with hit")
    print("costs already deducted. Chips are not played by any policy, so all")
    print("totals sit below a real chip-using season. Compare the columns, not")
    print("the absolute number.")
    print("=" * 84)


def main():
    parser = argparse.ArgumentParser(
        description="Simulate a real, transfer-constrained FPL season."
    )
    parser.add_argument("--seasons", nargs="+", default=["2024-25", "2025-26"])
    parser.add_argument("--policies", nargs="+", default=["baseline", "no_transfers",
                                                          "ft_margin_1.0", "ft_margin_1.5"],
                        help=f"any of: {', '.join(POLICIES)}")
    parser.add_argument("--start-gw", type=int, default=DEFAULT_START_GW)
    parser.add_argument("--stride", type=int, default=1,
                        help="simulate every Nth gameweek (2 or 3 for a fast look)")
    parser.add_argument("--augment", action="store_true",
                        help="also train on the seasons before each one")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("data_engine.transfer_optimizer").setLevel(logging.WARNING)
    logging.getLogger("data_engine.optimizer").setLevel(logging.WARNING)
    # The per-gameweek holdout warning fires on every one of ~37 refits and
    # says nothing about the policies being raced.
    logging.getLogger("data_engine.train_model").setLevel(logging.ERROR)

    unknown = [p for p in args.policies if p not in POLICIES]
    if unknown:
        raise SystemExit(f"Unknown policies: {unknown}. Choose from: {list(POLICIES)}")
    policies = [POLICIES[p] for p in args.policies]

    totals = {p.name: {"points": 0, "captain_points": 0, "transfers": 0,
                       "hits": 0, "hit_cost": 0, "gameweeks": 0} for p in policies}

    for idx, season in enumerate(args.seasons):
        logger.info("\n=== %s ===", season)
        season_df = backtest.load_season_frame(season, season_index=idx)

        prior = None
        if args.augment and idx > 0:
            frames = [backtest.load_season_frame(s, season_index=j)
                      for j, s in enumerate(args.seasons[:idx])]
            prior = feature_engineering.build_training_set(pd.concat(frames, ignore_index=True))

        res = simulate(season_df, policies, prior_seasons_df=prior,
                       start_gw=args.start_gw, stride=args.stride)
        for name, r in res.items():
            for k in totals[name]:
                totals[name][k] += r[k]

        # Per season as well as pooled: this project's standard is that a
        # change has to win EVERY season, because one big season can carry a
        # change that is actually harmful into looking like an improvement.
        _report(res, policies, title=f"SEASON {season}")

    if len(args.seasons) > 1:
        _report(totals, policies, title="BOTH SEASONS POOLED")


if __name__ == "__main__":
    main()
