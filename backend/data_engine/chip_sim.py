"""
File: chip_sim.py
Path: var-ified-xi/backend/data_engine/chip_sim.py

Chips in the season simulator (season_sim --chips; research/2026-11-chips).

Bench Boost, Triple Captain and Free Hit never change the squad carried into
the next week, so the realised gain of every chip can be scored in every week
of a simulated season without touching the season itself. Which weeks a
policy plays them in is then the only thing that separates two policies, and
they are compared on the same squads, week by week:

  * planner: production's chip planner (chip_planner.plan), asked each week
    with the chips it still holds; a chip it places in the current week is
    played;
  * fixture_rule: the habit of saving chips for blank and double gameweeks,
    fixed per half from the fixture calendar;
  * hindsight: each half's best placement on the realised gains, an upper
    bound no policy can reach;
  * hybrid: the Free Hit in the half's biggest blank, the planner timing the
    other chips (research/2026-11-freehit-blank). In a half with no blank it
    is the planner.

Chip rules as in 2025-26 and 2026-27: one of each per half, the first half's
by FIRST_HALF_DEADLINE. The Wildcard changes the squad, so it isn't here.
"""

from dataclasses import dataclass, field

import pandas as pd

import config
from data_engine import backtest, chip_planner

CHIPS = chip_planner.PLANNED                  # ("3xc", "bboost", "freehit")
FIRST_HALF_DEADLINE = 19
# GW2 builds the opening squad; chips are played from the first week it's carried.
FIRST_CHIP_GW = 3
POLICIES = ("planner", "fixture_rule", "hindsight", "hybrid")


def deadline_for(gw: int, last_gw: int) -> int:
    """The last gameweek this gameweek's chips can be played in."""
    return FIRST_HALF_DEADLINE if gw <= FIRST_HALF_DEADLINE else last_gw


def halves(rounds: list) -> list:
    """The chip-playing weeks of each half."""
    first = [g for g in rounds if FIRST_CHIP_GW <= g <= FIRST_HALF_DEADLINE]
    second = [g for g in rounds if g > FIRST_HALF_DEADLINE]
    return [h for h in (first, second) if h]


def fixture_counts(season_df: pd.DataFrame) -> dict:
    """{gw: {"doubles": clubs with two matches, "blanks": clubs with none}}."""
    clubs = season_df["team"].nunique()
    matches = (season_df.drop_duplicates(["round", "team", "kickoff_time"])
               .groupby(["round", "team"]).size())
    out = {}
    for gw, per_club in matches.groupby(level="round"):
        out[int(gw)] = {"doubles": int((per_club >= 2).sum()),
                        "blanks": int(clubs - len(per_club))}
    return out


def biggest_blank(gws: list, counts: dict):
    """The week with the most blank clubs, ties to the earlier; None without
    a blank. The fixture rule's Free Hit week."""
    weeks = [g for g in gws if counts.get(g, {}).get("blanks", 0) > 0]
    return max(weeks, key=lambda g: (counts[g]["blanks"], -g)) if weeks else None


def fixture_rule(gws: list, counts: dict) -> dict:
    """{chip: gw}: Free Hit in the biggest blank, Bench Boost in the biggest
    double, Triple Captain in the next-biggest double; whatever is left goes
    to the half's last free weeks (Triple Captain the deadline week, then
    Bench Boost, then Free Hit). Ties go to the earlier week."""
    taken, out = set(), {}

    def biggest(key):
        weeks = [g for g in gws if g not in taken and counts.get(g, {}).get(key, 0) > 0]
        if not weeks:
            return None
        gw = max(weeks, key=lambda g: (counts[g][key], -g))
        taken.add(gw)
        return gw

    for chip, key in (("freehit", "blanks"), ("bboost", "doubles"), ("3xc", "doubles")):
        gw = biggest(key)
        if gw is not None:
            out[chip] = gw
    last = [g for g in reversed(gws) if g not in taken]
    for chip in ("3xc", "bboost", "freehit"):
        if chip not in out and last:
            out[chip] = last.pop(0)
    return out


def hindsight(gws: list, gains: dict) -> dict:
    """{chip: gw}: the half's best placement on realised gains. A chip that
    would lose points in every week stays unplayed, as a manager who knew
    could leave it."""
    weeks = [{"gameweek": g, **{c: max(0.0, gains[g][c]) for c in CHIPS}}
             for g in gws if g in gains]
    return {p["chip"]: p["gameweek"] for p in chip_planner.assign(weeks, list(CHIPS))
            if p["value"] > 0}


def realised_gains(result: dict, squad: list, rows: pd.DataFrame, bench_value: dict,
                   normal_points: int, free_hit: dict = None) -> dict:
    """{chip: points it would have added this week}, against the week as it
    was really scored (normal_points). rows: the week's results with a row for
    every player in the squad and in the Free Hit squad."""
    actual = rows.set_index("player_id")[config.TARGET_COL].to_dict()
    minutes = rows.set_index("player_id")["minutes"].to_dict()
    positions = rows.set_index("player_id")["element_type"].to_dict()

    captain = result["captain_id"]
    if minutes.get(captain, 0) == 0 and result.get("vice_captain_id") is not None:
        captain = result["vice_captain_id"]
    scoring = backtest.apply_autosubs(result["starting_ids"], result["bench_ids"],
                                      minutes, bench_value, positions)
    armband = actual.get(captain, 0)

    gains = {
        # All fifteen count and nobody is subbed; the armband as usual.
        "bboost": sum(actual.get(p, 0) for p in squad) + armband - normal_points,
        # A third copy of whoever wore the armband, if he counted at all.
        "3xc": armband if captain in scoring else 0,
        "freehit": 0,
    }
    if free_hit:
        fh = backtest.score_gameweek(free_hit, rows, bench_value)["points"]
        gains["freehit"] = fh - normal_points
    return {c: int(v) for c, v in gains.items()}


def players_at(season_df: pd.DataFrame, gw: int, ids) -> pd.DataFrame:
    """Who's who at this deadline, for the chip planner: each player's latest
    row up to this gameweek (so a player whose club blanks keeps his last
    price)."""
    rows = (season_df[season_df["round"] <= gw].sort_values("round")
            .drop_duplicates("player_id", keep="last"))
    rows = rows[rows["player_id"].isin(set(ids))]
    return rows[["player_id", "web_name", "element_type", "team", "now_cost"]].reset_index(drop=True)


def xp_by_gw(per_gw: pd.DataFrame) -> dict:
    """{player_id: {gw: expected points}} from season_sim's horizon frame."""
    out = {}
    for r in per_gw.itertuples():
        out.setdefault(int(r.player_id), {})[int(r.target_gw)] = float(r.predicted_points)
    return out


@dataclass
class ChipLedger:
    """Every chip's realised gain, week by week, and the planner's plays."""
    rounds: list
    counts: dict
    gains: dict = field(default_factory=dict)        # gw -> {chip: points}
    planner: dict = field(default_factory=dict)      # chip, half -> gw
    held: list = field(default_factory=list)
    hybrid: dict = field(default_factory=dict)       # chip, half -> gw, halves with a blank
    hybrid_held: list = field(default_factory=list)

    def __post_init__(self):
        self.last_gw = max(self.rounds)
        self.half_weeks = halves(self.rounds)
        self._half = None
        # half -> the hybrid's Free Hit week, None where the half has no blank
        self.blank_week = {self.half_of(gws[0]): biggest_blank(gws, self.counts)
                           for gws in self.half_weeks}

    def half_of(self, gw: int) -> int:
        return 0 if gw <= FIRST_HALF_DEADLINE else 1

    def week(self, gw: int, per_gw: pd.DataFrame, season_df: pd.DataFrame, squad: list,
             result: dict, budget: int, rows_for, bench_value: dict, normal_points: int) -> None:
        """One week: ask the planner, then score every chip.

        per_gw: projections from this deadline out to the half's deadline.
        rows_for(ids): the week's results padded for those players.
        """
        if gw < FIRST_CHIP_GW:
            return
        half = self.half_of(gw)
        if half != self._half:                           # a new half, a new set
            self._half = half
            self.held = list(CHIPS)
            self.hybrid_held = [c for c in CHIPS if c != "freehit"]
        deadline = deadline_for(gw, self.last_gw)
        gameweeks = list(range(gw, deadline + 1))
        xp = xp_by_gw(per_gw)
        players = players_at(season_df, gw, xp)

        plan = chip_planner.plan(players, xp, gameweeks, self.held,
                                 {"now": {"label": "", "weeks": [{"gameweek": gw, "squad_ids": squad}]}},
                                 budget)
        free_hit = plan.get("free_hit")
        if free_hit is None:
            free_hit = chip_planner.free_hit_squads(players, xp, [gw], budget).get(gw)
        placed = plan["scenarios"][0]["plan"] if plan["scenarios"] else []
        for p in placed:
            if p["now"]:
                self.planner[(p["chip"], half)] = int(gw)
                self.held.remove(p["chip"])

        blank = self.blank_week.get(half)
        if blank is not None:
            # The Free Hit is fixed to the blank; the planner times the other
            # chips around it, never in that week.
            if gw == blank:
                self.hybrid[("freehit", half)] = int(gw)
            elif self.hybrid_held:
                hplan = chip_planner.plan(
                    players, xp, gameweeks, self.hybrid_held,
                    {"now": {"label": "", "weeks": [{"gameweek": gw, "squad_ids": squad}],
                             "blocked": {blank}}},
                    budget)
                for p in (hplan["scenarios"][0]["plan"] if hplan["scenarios"] else []):
                    if p["now"]:
                        self.hybrid[(p["chip"], half)] = int(gw)
                        self.hybrid_held.remove(p["chip"])

        fh = None
        if free_hit:
            fh = {k: free_hit[k] for k in ("starting_ids", "bench_ids", "captain_id", "vice_captain_id")}
        rows = rows_for(list(dict.fromkeys(list(squad) + (free_hit["squad_ids"] if free_hit else []))))
        self.gains[gw] = realised_gains(result, squad, rows, bench_value, normal_points, fh)

    def placements(self) -> dict:
        """{policy: {(chip, half): gw}}."""
        out = {"planner": dict(self.planner), "fixture_rule": {}, "hindsight": {},
               "hybrid": {**{k: gw for k, gw in self.planner.items()
                             if self.blank_week.get(k[1]) is None},
                          **self.hybrid}}
        for half, gws in enumerate(self.half_weeks):
            gws = [g for g in gws if g in self.gains]
            for chip, gw in fixture_rule(gws, self.counts).items():
                out["fixture_rule"][(chip, half)] = gw
            for chip, gw in hindsight(gws, self.gains).items():
                out["hindsight"][(chip, half)] = gw
        return out

    def per_gw(self, base: list) -> dict:
        """{policy: [{"gw", "points"}]}: the reference's weekly scores plus
        the chips each policy played."""
        out = {}
        for policy, placed in self.placements().items():
            extra = {}
            for (chip, _), gw in placed.items():
                extra[gw] = extra.get(gw, 0) + self.gains[gw][chip]
            out[policy] = [{"gw": g["gw"], "points": g["points"] + extra.get(g["gw"], 0)}
                           for g in base]
        return out

    def unplayed(self) -> list:
        """(chip, half) the planner still held when its half ran out."""
        return [(c, h) for h, gws in enumerate(self.half_weeks) if any(g in self.gains for g in gws)
                for c in CHIPS if (c, h) not in self.planner]

    def summary(self) -> dict:
        """{policy: [(chip, half, gw, points)]}, for the log and the results file."""
        return {policy: sorted((chip, half, int(gw), int(self.gains[gw][chip]))
                               for (chip, half), gw in placed.items())
                for policy, placed in self.placements().items()}
