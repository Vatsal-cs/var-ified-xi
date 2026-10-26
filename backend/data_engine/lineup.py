"""
File: lineup.py
Path: var-ified-xi/backend/data_engine/lineup.py

Picks the starting XI and bench order from a squad you already own,
valuing each lineup by what it scores AFTER FPL's automatic substitutions.

The optimizers choose the XI on expected points, which treats a benched
player as worth (almost) nothing. That's right for a player who never comes
on, and wrong for the first sub behind a starter who might not play. Starting
a 60% starter worth 6 if he plays, with a sure starter worth 4 on the bench,
expects 0.6 x 6 + 0.4 x 4 = 5.2; starting the sure one expects 4. Expected
points calls it the other way (3.6 vs 4).

Every legal XI and bench order is scored here (one keeper choice, then
286 outfield benches x 6 orders) over simulated "who played" draws,
replaying the autosub rule as backtest.apply_autosubs does: each starter
who didn't play, in pitch order, is replaced by the first bench player who
played and keeps the formation legal. Points are expected points given that
he plays, so only the play/no-play pattern is simulated. The same draws score
every lineup, so the comparison between lineups is far less noisy than the
absolute values.
"""

import itertools

import numpy as np

import config

GK, DEF, MID, FWD = 1, 2, 3, 4
OUTFIELD = (DEF, MID, FWD)
DRAWS = 4000


def choose_lineup(squad_ids: list, positions: dict, p_play: dict, points: dict,
                  draws: int = DRAWS, seed: int = 0):
    """(starting_ids, bench_ids in autosub order, expected points), or None
    when the squad isn't a full 2/5/5/3 or nobody is projected to play.

    positions: element_type per player. p_play: probability he plays at all.
    points: expected points (so points / p_play is what he scores if he plays).
    """
    squad = list(squad_ids)
    by_pos = {pos: [p for p in squad if positions.get(p) == pos] for pos in (GK, *OUTFIELD)}
    if [len(by_pos[p]) for p in (GK, *OUTFIELD)] != [config.SQUAD_POSITION_LIMITS[p]
                                                     for p in (GK, *OUTFIELD)]:
        return None

    prob = {p: float(np.clip(p_play.get(p, 0.0), 0.0, 1.0)) for p in squad}
    if_played = {p: (float(points.get(p, 0.0)) / prob[p] if prob[p] > 0.01 else 0.0)
                 for p in squad}

    # Keepers: only a keeper can replace a keeper, so this half is separate.
    g1, g2 = by_pos[GK]
    def keeper_value(first, second):
        return prob[first] * if_played[first] + (1 - prob[first]) * prob[second] * if_played[second]
    gk_start, gk_bench = (g1, g2) if keeper_value(g1, g2) >= keeper_value(g2, g1) else (g2, g1)

    outfield = by_pos[DEF] + by_pos[MID] + by_pos[FWD]
    pos_arr = np.array([positions[p] for p in outfield])
    value = np.array([if_played[p] for p in outfield])
    rng = np.random.default_rng(seed)
    played = rng.random((draws, len(outfield))) < np.array([prob[p] for p in outfield])

    lo = {pos: config.STARTING_XI_LIMITS[pos][0] for pos in OUTFIELD}
    hi = {pos: config.STARTING_XI_LIMITS[pos][1] for pos in OUTFIELD}
    best = None
    for bench in itertools.combinations(range(len(outfield)), 3):
        starters = [i for i in range(len(outfield)) if i not in bench]
        counts = {pos: int((pos_arr[starters] == pos).sum()) for pos in OUTFIELD}
        if any(not lo[pos] <= counts[pos] <= hi[pos] for pos in OUTFIELD):
            continue
        base = played[:, starters] @ value[starters]
        missing = {pos: (~played[:, [i for i in starters if pos_arr[i] == pos]]).sum(axis=1)
                   for pos in OUTFIELD}
        for order in itertools.permutations(bench):
            total = base + _sub_points(order, pos_arr, value, played, counts, missing, lo)
            score = float(total.mean())
            if best is None or score > best[0]:
                best = (score, starters, order)

    if best is None:
        return None
    score, starters, order = best
    starting = [gk_start] + [outfield[i] for i in starters]
    bench_ids = [gk_bench] + [outfield[i] for i in order]
    return starting, bench_ids, round(score + keeper_value(gk_start, gk_bench), 3)


def _sub_points(order, pos_arr, value, played, counts, missing, lo):
    """Points the bench adds in each draw: starters who didn't play are
    taken in pitch order (defenders, midfielders, forwards), each replaced by
    the first unused bench player who played and keeps the shape legal."""
    n = played.shape[0]
    cnt = {pos: np.full(n, counts[pos]) for pos in OUTFIELD}
    left = {pos: missing[pos].copy() for pos in OUTFIELD}
    used = {b: np.zeros(n, dtype=bool) for b in order}
    added = np.zeros(n)
    for pos in OUTFIELD:
        for _ in range(int(left[pos].max(initial=0))):
            pending = left[pos] > 0
            done = np.zeros(n, dtype=bool)
            for b in order:
                q = pos_arr[b]
                ok = pending & ~done & played[:, b] & ~used[b]
                if q != pos:
                    ok &= (cnt[pos] - 1) >= lo[pos]
                if not ok.any():
                    continue
                used[b] |= ok
                done |= ok
                added += np.where(ok, value[b], 0.0)
                if q != pos:
                    cnt[pos] = cnt[pos] - ok
                    cnt[q] = cnt[q] + ok
            # A missing starter nobody could replace still uses up his turn.
            left[pos] = left[pos] - pending
    return added
