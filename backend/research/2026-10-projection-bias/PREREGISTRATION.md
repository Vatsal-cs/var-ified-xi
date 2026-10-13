# Projection bias by player type — pre-registration
Written 2026-10-12 19:15 MDT, before any run. Commit 58d5a37.

Why: in 2026-27 GW6 the model started Murillo (projected 4.29, mostly a
defensive-contribution floor) over De Cuyper (2.74) and João Pedro (3.45),
both averaging more. One week proves nothing; these tests ask whether the
model is *systematically* wrong about these player types, on seasons it was
not tuned against this week.

This is a diagnostic, not a model change. Nothing ships from it. A test that
flags a bias earns a targeted fix, which then goes through the usual paired
backtest on points (5 seeds, tuning seasons, then the held-back seasons once
where the data allows).

## Data
Walk-forward replay of the shipping model (two-stage, 5-model seed bag, seed
42, injury flags attached) over the tuning seasons, gameweeks 2-38:
2024-25 trained on itself; 2025-26 trained on itself plus 2024-25 — the
settings every earlier backtest used. One prediction per match, summed per
player-gameweek. Recorded per player-gameweek: projection, P(60+) after the
injury rule, the points-if-60+ regressor's value, actual points and minutes.

Every segment below is defined from information available at the deadline
(form features, previous matches, injury flag), never from the outcome.

Residual = actual points - projected points. Intervals: 95%, bootstrap over
gameweeks (2000 resamples). Pool P = player-gameweeks projected >= 2.5
points, the range where start/bench and transfer calls are made.

## T1 — steady defenders vs attackers (2025-26 only: defensive contribution
points started that season)
- S: defenders in P with dc_avg_5 >= 10 (meet the defender threshold on
  average).
- A: midfielders and forwards in P in the top third of xgi_avg_3 (within
  the season's pool), plus defenders in P in the top third of xgi_avg_3
  among the pool's defenders.
- Statistic: mean residual(A) - mean residual(S).
- BIAS if >= +0.3 points per match with the interval above zero.

## T2 — one missed match over-penalised
- B: player-gameweeks (any projection) whose previous match was 0 minutes,
  the two matches before that both 60+, and who are flagged fit at the
  deadline (status "a", chance of playing blank or 100).
- Statistic: actual 60+ rate - mean predicted P(60+).
- BIAS if >= +0.10 with the interval above zero, pooled over both seasons.
- Control reported alongside: the same players' type with no blank (previous
  three matches all 60+).

## T3 — big single scores over-discounted
- Rows in P that played in at least 4 of their last 5 matches with at least
  20 points across them. Haul share = best single match / total of the last 5.
- H: haul share >= 0.5. L: haul share <= 0.35.
- Statistic: mean residual(H) - mean residual(L).
- BIAS if >= +0.3 with the interval above zero, pooled over both seasons.

Each test is also reported per season. Where a season disagrees in sign with
the pooled verdict, that is stated next to it.

## Descriptive only
- Residual by position and by xgi_avg_3 third, both seasons.
- For each group: P(60+) calibration and the points-if-60+ regressor's bias
  on rows that did play 60+, to say whether a gap is about minutes or about
  points.
- The same tables for 2026-27 GW2-6 (live season, current model with last
  season's team ratings). Small sample; not used for any verdict.
