# Points distributions — are the probabilities honest?

Written 2026-10-14, before validate.py was first run.

`data_engine/distributions.py` turns each projection into a full distribution
of scores, so the dashboard can say "Haaland outscores Saka 64% of the time"
or "18% chance of 10+". Those numbers are only worth showing if they come true
about as often as they say. This checks that on seasons the tables weren't
fitted on: fit on 2024-25, test on 2025-26, and the other way round.

Data: the walk-forward rows from research/2026-10-projection-bias (every
player-match of both seasons, projected without seeing the result).
Single-match gameweeks only.

## Checks and what passes

1. **Range.** The 10th–90th percentile range should hold the real score at
   least 80% of the time (scores are whole numbers, so it can be more).
2. **Chance of 10+.** By tenths of the predicted chance, predicted and actual
   rates within 3 percentage points in most bins.
3. **A outscores B.** Two players in the same gameweek, both projected 2.5+,
   ties left out. In bins of the favourite's predicted chance, predicted and
   actual within 3 percentage points in most bins, and a Brier score below a
   coin flip's 0.25.

If a check fails, the dashboard doesn't show that number until it's fixed.

## Result

Run 2026-10-14 (`python research/2026-10-distributions/validate.py`, output.txt).

| Check | fit 2024-25 → test 2025-26 | fit 2025-26 → test 2024-25 | Pass? |
|---|---|---|---|
| 10–90 range holds the real score | 93.3% (pool 87.6%) | 91.7% (pool 85.2%) | ✅ (a little wide) |
| Chance of 10+, predicted vs actual by tenths | within 2 points in every bin | within 2 points in every bin | ✅ |
| A outscores B, straight from the distributions | Brier 0.2427; within 3 points up to 70% | Brier 0.2449; within 3 points only up to 60% | ❌ overconfident |

**The head-to-heads failed as built**: a "70%" favourite won about 65–68%, and
the gap grows with confidence. It isn't teammates moving together; pairs from
different clubs are just as overconfident. Each player's own range and 10+
chance are honest; only the comparison overstates the gap.

**Fix, added after seeing that** (so it is a post-hoc correction, stated as
such): scale the log-odds of every head-to-head by one number, fitted on both
seasons' pairs: **0.73** (`distributions.PAIR_LOGIT_SCALE`). After it:

| Favourite's chance | 2025-26 predicted / actual | 2024-25 predicted / actual |
|---|---|---|
| 50–55% | 52.4 / 52.6 | 52.4 / 52.3 |
| 55–60% | 57.3 / 58.4 | 57.3 / 56.3 |
| 60–65% | 62.1 / 63.6 | 62.1 / 61.1 |
| 65–70% | 66.7 / 68.4 | 67.0 / 65.1 |
| 70–75% | 71.8 / 72.4 | 72.3 / 66.9 |
| 75–80% | 77.2 / 76.7 | 77.3 / 73.2 |

2025-26 is within 2 points everywhere; 2024-25 within 2 up to 70% and still
overconfident above it. 2024-25's projections were trained on that season
alone, 2025-26's on two seasons; the live model trains on three plus the
current one, so it sits closer to 2025-26. The dashboard shows head-to-heads
recalibrated and drops the "top scorer of your XI" figure, which had no
honest equivalent check.

### Found on the way: top projections run high

Grouping real scores by the points-if-60+ projection shows the model's
highest projections come in low: midfielders projected 8+ when they play
averaged 6.6–6.8, forwards projected ~8.2 averaged 6.3, while the lowest
projections undershoot a little (projected 2.4, scored 2.9). The distributions use what
really happened, so they're unaffected — which is why Haaland's distribution
averages ~6 when his projection says 7.8. Whether shrinking the projections
themselves would score more points is a separate question for the backtest,
not settled here.

## Update, October 2026: group averages made to rise with the projection

The small top groups were noisy enough to run backwards: forwards projected
6.2 if they played 60+ really averaged 4.5, below those projected 5.5 (5.0),
and keepers had the same kind of dip. A player projected just above 6
(Haaland, GW8 2026-27) inherited it: his distribution averaged 4.2 against a
5.7 projection. `distributions.MONOTONE_MEANS` now pools out-of-order
neighbouring groups to their match-weighted average and shifts each group's
distribution to it, shape kept.

Same checks, same split (`output_monotone.txt`), before → after:

| | fit 2024-25 → test 2025-26 | fit 2025-26 → test 2024-25 |
|---|---|---|
| 10–90 range holds the score (pool) | 87.6% → 88.2% | 85.2% → 85.6% |
| A outscores B, Brier (recalibrated) | 0.2425 → 0.2422 | 0.2434 → 0.2433 |
| Chance of 10+ by tenths | within 2 points, as before | within 2 points except one bin at 3 |

Equal or slightly better everywhere, so it ships. The log-odds scale refits
to 0.75 on the new tables (was 0.73) and is updated to match.

What the smoothing doesn't change: the top groups still score less than the
model projects (players projected 7.95 if they play averaged 6.23; Haaland,
projected 8.65 at his highest, averaged 7.0). That's the projection running
high at the top, which the distributions report honestly.
