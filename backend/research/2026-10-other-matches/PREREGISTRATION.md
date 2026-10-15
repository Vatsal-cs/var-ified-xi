# Matches FPL doesn't show — pre-registration
Written 2026-10-15 05:10 MDT, before any backtest run with these inputs.
Amended 05:45 MDT, still before any run: added the form inputs and the
second variant below, at the user's request.

Why: FPL's data is Premier League only. The model can't see a Champions
League game on Wednesday, a League Cup tie, or a player flying to South
America for two qualifiers, which decide who is tired or rested on Saturday.

## Data (data_engine/other_matches.py)
ESPN's public JSON feed (unofficial, cached): Champions League, Europa
League, Conference League, League Cup and FA Cup matches of every Premier
League club, and every international match (friendlies, Nations League, all
World Cup qualifying zones, AFCON and qualifiers, Asian Cup, CONCACAF Nations
League, Euro qualifiers), each with every player's role (started / came on /
unused) and the venue's country. ESPN players are linked to FPL players by
name within each club's season squad: 96.7-98.2% of players with 900+
minutes linked in 2022-23, 2024-25 and 2025-26 (the misses are mostly
Brazilians listed under full legal names; they get the club-level inputs).

## Inputs added (per Premier League match, known before kick-off)
- xm_days_before — days since the club's last other match (cap 14)
- xm_days_after — days until its next other match (cap 14)
- xm_count_14 — other matches in the 14 days before
- xm_started_before / xm_rested_before — whether the player started the
  club's last other match, if it was within 7 days and has been played
- intl_apps_14 / intl_starts_14 — his international appearances / starts in
  the 14 days before
- intl_far_14 — any of them outside Europe
- intl_days_before — days since his last international appearance (cap 21)

Form in those games (second variant only), from each match page's player
stats, cup + European + international combined, 30 days before kick-off:
- xm_apps_30 — appearances
- xm_ga_30 — goals + assists
- xm_shots_30, xm_sot_30 — shots, shots on target

## Primary — backtest, points
production vs **other_matches** (rest and load inputs) and
**other_matches_form** (the same plus form in those games), seeds 42, 7, 13,
101, 2024; 2024-25 (trained
on itself) and 2025-26 (plus 2024-25); gameweeks 2-38; injury flags on;
--bag-size 1 both sides. Pooled with data_engine.evaluation.

**ACCEPT** a variant on the tuning seasons only if the verdict is "better"
(pooled 95% CI above zero AND ahead in both seasons); if both are, the larger
pooled gain goes forward. Then run it ONCE on 2022-23 (trained
on itself) and 2023-24 (plus 2022-23), 5 seeds, logged in config's "Uses so
far"; ship (config.OTHER_MATCHES = True, with that variant's inputs) only if the paired difference is
> 0 in both. Otherwise it stays off and the result is recorded either way.

## Descriptive only
MAE, rank correlation, Brier P(60+) — Brier is the most direct check, since
most of what these inputs can know is about who plays. The dashboard shows
your players' other matches whatever the verdict.
