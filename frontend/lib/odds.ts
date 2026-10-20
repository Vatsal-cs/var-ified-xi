// File: odds.ts
// Path: var-ified-xi/frontend/lib/odds.ts
//
// Comparisons between two players' points distributions (Player.dist.pmf,
// index = score). Treated as independent, which slightly overstates how often
// two teammates' scores differ — fine for "who's likelier to score more".

import type { Player } from "./types";

/** P(a scores more than b), and P(they tie). */
export function beats(a: number[], b: number[]): { win: number; tie: number } {
  let below = 0;
  let win = 0;
  let tie = 0;
  const n = Math.max(a.length, b.length);
  for (let i = 0; i < n; i++) {
    const pa = a[i] ?? 0;
    const pb = b[i] ?? 0;
    win += pa * below;
    tie += pa * pb;
    below += pb;
  }
  return { win, tie };
}

/** P(a outscores b), ties left out: the head-to-head read. Straight from two
 *  distributions it comes out overconfident, so the log-odds are scaled by
 *  the factor fitted on past seasons (backend distributions.PAIR_LOGIT_SCALE,
 *  shipped in the JSON as odds_calibration). */
export function headToHead(a: number[], b: number[], scale = 1): number {
  const ab = beats(a, b).win;
  const ba = beats(b, a).win;
  if (ab + ba <= 0) return 0.5;
  const p = Math.min(Math.max(ab / (ab + ba), 1e-6), 1 - 1e-6);
  return 1 / (1 + Math.exp(-scale * Math.log(p / (1 - p))));
}

const XI_LIMITS: Record<Player["position"], [number, number]> = {
  GK: [1, 1],
  DEF: [3, 5],
  MID: [2, 5],
  FWD: [1, 3],
};

/** The starter a bench player would most plausibly replace: the lowest-
 *  projected one whose swap still leaves a legal formation. */
export function swapTarget(benchPlayer: Player, xi: Player[]): Player | undefined {
  const counts: Record<string, number> = { GK: 0, DEF: 0, MID: 0, FWD: 0 };
  for (const p of xi) counts[p.position]++;
  const legal = xi.filter((s) => {
    if ((s.position === "GK") !== (benchPlayer.position === "GK")) return false;
    const c = { ...counts };
    c[s.position]--;
    c[benchPlayer.position]++;
    return (Object.keys(XI_LIMITS) as Player["position"][]).every(
      (pos) => c[pos] >= XI_LIMITS[pos][0] && c[pos] <= XI_LIMITS[pos][1]
    );
  });
  return legal.sort((a, b) => a.predicted_points - b.predicted_points)[0];
}

export const pct = (x: number) => `${Math.round(x * 100)}%`;

/** A start/bench call too close to call: a bench player and a starter he
 *  could legally replace, each likelier than 40% to outscore the other. */
export type CoinFlip = { starter: Player; sub: Player; p: number };

export const COIN_FLIP = { lo: 0.4, hi: 0.6 };

/** Every bench player's closest call against a starter he could replace
 *  (keepers only with keepers), closest to 50/50 first. p is the bench
 *  player's chance of outscoring the starter, ties left out. */
export function coinFlips(xi: Player[], bench: Player[], scale = 1): CoinFlip[] {
  const counts: Record<string, number> = { GK: 0, DEF: 0, MID: 0, FWD: 0 };
  for (const s of xi) counts[s.position]++;
  const legal = (sub: Player, s: Player) => {
    if ((s.position === "GK") !== (sub.position === "GK")) return false;
    const c = { ...counts };
    c[s.position]--;
    c[sub.position]++;
    return (Object.keys(XI_LIMITS) as Player["position"][]).every(
      (pos) => c[pos] >= XI_LIMITS[pos][0] && c[pos] <= XI_LIMITS[pos][1]
    );
  };
  const out: CoinFlip[] = [];
  for (const sub of bench) {
    if (!sub.dist) continue;
    const calls = xi
      .filter((s) => s.dist && legal(sub, s))
      .map((s) => ({ starter: s, sub, p: headToHead(sub.dist!.pmf, s.dist!.pmf, scale) }))
      .filter((c) => c.p >= COIN_FLIP.lo && c.p <= COIN_FLIP.hi)
      .sort((a, b) => Math.abs(a.p - 0.5) - Math.abs(b.p - 0.5));
    if (calls[0]) out.push(calls[0]);
  }
  return out.sort((a, b) => Math.abs(a.p - 0.5) - Math.abs(b.p - 0.5));
}
