# Are players who just played in Europe projected wrong? — pre-registration
Written 2026-10-15 ~09:00 MDT, before the run.

The shipped model (with the other-matches rest and load inputs, config
OTHER_MATCHES) replayed walk-forward over 2024-25 and 2025-26 (collect.py,
5-model bag, seed 42), every player-match projected 2.5+.

Groups, by the club's last cup/European match before the Premier League
game: S = it was within 4 days and the player started it; R = within 4 days
and he didn't start it; N = no such match within 7 days.

Statistic per group: mean residual (actual − projected) and actual vs
predicted P(60+), bootstrap over gameweeks. **BIAS** for a group if its mean
residual differs from N's by ≥ 0.3 points with the 95% interval excluding
zero, or its 60+ rate differs from predicted by ≥ 0.05 with the interval
excluding zero. Any bias found is reported as-is; fixing it would be a new
pre-registered test.
