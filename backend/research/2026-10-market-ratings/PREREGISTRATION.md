# Team ratings from betting odds — pre-registration
Written 2026-10-15 16:57 MDT, before any run. Commit 17b0702.

Why: rating 2025-26 with its own FPL ratings instead of 2024-25's was worth
+107 [+17, +198] points that season (research/2026-10-lagged-team-form). The
live model only has last season's ratings, and FPL publishes none for 2026-27.
Team form from actual xG has now failed three ways. The betting market is the
sharpest free measure of team strength (football-data.co.uk closing odds, no
key); this season it agrees closely with an independent fixture-difficulty
table and disagrees with our ratings on Palace, Spurs, Villa and Brighton.

## Variant (backtest.py "lagged_market_add")
lagged_ratings (every past season rated with the previous season's FPL
ratings, as live) plus team_form.py's six columns built from ODDS instead of
xG (config.TEAM_FORM_SOURCE = "odds"): for each match, the goals the market
expected each side to score (odds_data.py: de-margined average 1X2 plus
over/under 2.5), recency-weighted per team over matches strictly before
(decay 0.9, prior worth 4 matches = last season's final market rating pulled
halfway to the league mean; promoted clubs = the relegated clubs' average).
No opponent adjustment — the same machinery the xG version used.

## Primary — backtest, points
lagged_market_add vs lagged_ratings, seeds 42, 7, 13, 101, 2024; 2024-25
(trained on itself) and 2025-26 (plus 2024-25); --bag-size 1.
ACCEPT only if "better" (pooled 95% CI above zero AND ahead in both seasons);
then ONCE on 2022-23 and 2023-24, logged in config's "Uses so far"; ship
(live odds ratings) only if > 0 in both. Anything else: not used, and the
result goes in the ledger.

## Descriptive only
Compared with lagged_team_form_add (xG version, same settings) from
research/2026-10-lagged-team-form.
