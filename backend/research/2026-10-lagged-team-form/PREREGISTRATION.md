# This season's team form, tested the way the live model runs — pre-registration
Written 2026-10-15 15:42 MDT, before any run.

Why: Brighton players have beaten their projections by more than any other
club's this season (GW2-6, rows with 60+ minutes: +2.7 points per player-game
against a league spread of -0.3 to +1.7). The live model rates Brighton by last
season's FPL ratings (attack 5th, defence 6th-7th); this season they have
scored the most (18) and conceded the fewest (5). Rated like Man City, with
Palace rated weak, Groß's GW7 projection would go 3.81 -> 4.43, De Cuyper's
3.62 -> 4.66.

Both earlier team-form tests (research/2026-10-team-form, -team-form-add)
replayed past seasons with THAT season's own FPL ratings, a single archived
snapshot that may carry hindsight. The live model has no such ratings: it uses
the season before's. If the snapshot already knows how good each team turned
out, adding this season's form can't show a gain in those tests, however much
it would help live. This test runs both sides the way live works.

## Variants (backtest.py)
- lagged_ratings (reference): production, with every past season rated by the
  PREVIOUS season's FPL ratings (promoted clubs = the relegated clubs' average),
  as the live model is in 2026-27.
- lagged_team_form_add: the same, plus team_form.py's columns (team_xg_for,
  team_xg_against, opp_xg_for, opp_xg_against, match_xg_for, match_xg_against),
  exactly as in the team_form_add test.
- production (descriptive only): the season's own ratings. production minus
  lagged_ratings says how much the archived ratings know that live doesn't.

## Primary — backtest, points
lagged_team_form_add vs lagged_ratings, seeds 42, 7, 13, 101, 2024; 2024-25
(trained on itself) and 2025-26 (plus 2024-25); --bag-size 1.
ACCEPT only if "better" (pooled 95% CI above zero AND ahead in both seasons);
then ONCE on 2022-23 and 2023-24 (same settings, 2023-24 trained with 2022-23),
logged in config's "Uses so far"; ship (team form added live) only if > 0 in
both. Anything else: not used, and the result goes in the ledger.

## Descriptive only
- production vs lagged_ratings, both tuning seasons.
- Nothing else is decided from this run.
