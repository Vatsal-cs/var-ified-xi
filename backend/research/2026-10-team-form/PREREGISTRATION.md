# Team form (xG-based team strength) — pre-registration
Written 2026-10-11 08:29 MDT, before any run.

Change: replace FPL's published team strength features (team/opp attack and
defence, fixture difficulty) with team_form.py — each team's recency-weighted
xG for and against from matches strictly before each game (decay 0.9/match,
4-match prior = last season's final rating halfway to league mean; promoted =
relegated clubs' average), plus match_xg_for/against. Point-in-time, same
definition for every season and for live predictions.

Note on fairness: the archive's FPL ratings are one snapshot per season, so the
"production" side of past-season backtests may carry hindsight; that can only
flatter production.

Primary — backtest, production vs team_form, seeds 42, 7, 13, 101, 2024, seasons
2024-25 and 2025-26, single model per fit (--bag-size 1, both sides).
ACCEPT on tuning seasons only if the verdict is "better" (pooled 95% CI above
zero AND ahead in both seasons). Then run ONCE on 2022-23 and 2023-24 (5 seeds);
ship (config.TEAM_FORM = True) only if the paired difference is > 0 in both.
Descriptive only: replay of 2026-27 GW2-5 vs the last-season-ratings fallback.
commit e92affe
