# Bookings — pre-registration
Written 2026-11-08, before any run. Runs on GitHub Actions.

Why: in GW10 Thiago was sent off after 22 minutes (−2) and is now banned
until 5 December. The user asked why the model doesn't count cards. Card
points (−1 a yellow, −3 a red) are already in every score the model learns
from, but no input says which players get booked, so a player booked every
other game is projected like one who never is. The ban itself is already
handled: FPL flags him suspended with a return date, and the plan treats
that like an injury (horizon_availability).

Thiago's red wasn't something a card rate predicts (no reds before it, four
yellows in ten games), so the question here is the general one: does
knowing who gets booked score more points?

## Variants (backtest.py)
- lagged_ratings (reference): production with each past season's teams
  rated on the previous season's FPL ratings, as the live model runs.
- bookings: lagged_ratings plus three inputs: yellow cards averaged over the
  last ten gameweeks and over the season so far (`yellow_avg_10`,
  `yellow_avg_season`), and red cards over the season (`red_avg_season`).
  Training rows exclude their own match; prediction rows include the latest
  match, as the existing windows do.

## Primary — backtest, points
bookings vs lagged_ratings, seeds 42, 7, 13, 101, 2024; 2024-25 (trained on
itself) and 2025-26 (plus 2024-25); --bag-size 1.

- "Better" (pooled 95% CI above zero AND ahead in both seasons): run ONCE on
  the held-back 2022-23 and 2023-24 (same variants and seeds), logged in
  config's "Uses so far". Ship only if it is above zero in both.
- Anything else: not shipped. The inputs stay built (they cost nothing live)
  but are not model inputs, and the answer to "why doesn't it count cards"
  is that knowing who gets booked doesn't score more points.

Expectation, stated up front: small. A yellow is −1, and the gap between a
frequent and a rare booker is about a quarter of a point a match. Since
long-run form shipped, five more added-input tests have shown no detectable
effect or done worse.

## Not tested
Ban risk for a player on four yellows (a fifth before GW19 means a one-match
ban). It only touches the weeks after his next booking, and FPL flags the
ban itself once it happens.
