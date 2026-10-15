# Form adjusted for the opponent — result

**No detectable effect for any of the three. Production is unchanged.**
Pre-registered in PREREGISTRATION.md (commit 83b7b8d) before any run.

| Variant | 2024-25 | 2025-26 | Pooled, 95% CI | Runs ahead | Verdict |
|---|---:|---:|---:|---:|---|
| sched — strength of the last five PL opponents | +8 | +10 | +18 [−65, +99] | 7 / 10 | no detectable effect |
| form_adj — PL xG, xGI, points scaled by opponent strength | +16 | −5 | +11 [−45, +66] | 3 / 10 | no detectable effect |
| other_form_adj — cup/European/international form weighted by opponent Elo | −15 | −2 | −17 [−113, +87] | 3 / 10 | no detectable effect |

(`evaluation.txt`; production here already includes the other-matches rest
and load inputs.) None is "better", so nothing went to the held-back seasons.

## What it means
The model already sees each upcoming opponent's strength and its own
underlying-chance form (xG, xA); adjusting past form for the opponents faced
adds nothing it can turn into points. Goals and shots in cup, European and
international games — raw (research/2026-10-other-matches, +81 [−4, +168])
or weighted by opponent Elo (here, −17) — don't help predict Premier League
points either.

## Data built for it
Club Elo from every Champions/Europa/Conference League and English cup result
since 2022 (`other_matches.club_ratings`; ClubElo's feed was down), national
teams from eloratings.net. Kept in the code for later tests.
