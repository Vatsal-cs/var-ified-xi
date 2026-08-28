// File: PipelineExplainer.tsx
// Path: var-ified-xi/frontend/components/PipelineExplainer.tsx
//
// This is a genuine 5-stage sequence (the actual order backend/main.py
// executes in), so numbered stage markers are earned here, not decorative.

const STAGES = [
  {
    tag: "01",
    title: "Data Capture",
    summary: "Pulls the raw material straight from FPL's free public API.",
    body: [
      "Every run starts by fetching three things from fantasy.premierleague.com: the full player and team list, the season's fixture list, and a gameweek-by-gameweek history for every single player in the game (600+ individual calls, cached locally so re-runs on the same day are instant).",
      "This is real official data, not scraped or estimated — minutes played, goals, assists, bonus points, ICT index, and more, for every past match.",
    ],
  },
  {
    tag: "02",
    title: "Feature Model",
    summary: "Turns raw match history into rolling form signals.",
    body: [
      "Raw stats alone don't predict much — a striker's one big haul three months ago says little about next week. So each player's history is converted into rolling averages over their last 3 and 5 gameweeks: minutes, points, ICT index, influence, creativity, and threat.",
      "Every rolling average is shifted back by one gameweek before being used, so the model is never accidentally shown the answer it's trying to predict. Fixture difficulty is also folded in, comparing a player's attacking team strength against their next opponent's defensive strength.",
    ],
  },
  {
    tag: "03",
    title: "Prediction Engine",
    summary: "Two models, because \"will he play?\" and \"how well?\" are different questions.",
    body: [
      "Rotation risk is the single biggest source of error in fantasy football, so it gets its own model rather than being smeared into one number. A classifier estimates the odds a player doesn't play at all, comes off the bench, or starts properly. A second model then estimates how many points he scores given that he did start — trained only on players who actually played 60 minutes, so it learns quality rather than availability. Multiply the two together and you get expected points.",
      "Both are gradient-boosted tree models trained on this season plus the three before it — over 40,000 real gameweek results. Accuracy is measured on gameweeks the model never saw, and only then is it retrained on everything, so it goes into the weekend having learned from the most recent form rather than being deliberately blind to it. Injured, suspended and doubtful players are dampened using FPL's own status flags, plus a record of who has been flagged repeatedly this season.",
    ],
  },
  {
    tag: "04",
    title: "Constraint Solver",
    summary: "A real optimizer, planning several gameweeks at once.",
    body: [
      "This is the part that separates it from a spreadsheet sort. A Mixed-Integer Linear Program (solved with PuLP/CBC) decides everything simultaneously: which 15 players fill the squad, which 11 start, who wears the armband — and, when it knows your real team, which transfers to make in each of the next six gameweeks.",
      "It's bound by every real FPL rule: a £100.0m budget, an exact 2/5/5/3 squad split, a valid formation, no more than 3 players from one club, one free transfer per week banked up to five, and −4 points for each extra. Planning six weeks at once is what stops it chasing a single good fixture into a wall of hard ones — and it's the only way to find moves like banking a transfer this week to afford two next week.",
    ],
  },
  {
    tag: "05",
    title: "Decision",
    summary: "The confirmed squad, written out and shown above.",
    body: [
      "The solver's output — starting XI, bench, captain, vice-captain and the transfer plan — gets written to a single JSON file. This exact page reads that file directly. There's no live server making these picks on request; everything above came from one offline solve.",
      "A scheduled job re-runs the whole engine in the day before each deadline and commits the result, which redeploys this page automatically. Every number here is regenerated from fresh form, fresh prices and a fresh solve.",
    ],
  },
];

export default function PipelineExplainer() {
  return (
    <section aria-labelledby="pipeline-heading" className="mx-auto max-w-3xl">
      <h2
        id="pipeline-heading"
        className="mb-1 font-display text-2xl uppercase tracking-tight text-ink-100"
      >
        How the decision was made
      </h2>
      <p className="mb-6 font-body text-sm text-ink-300">
        Five stages, run in order, every time. Expand any stage for the actual mechanics behind it.
      </p>

      <div className="divide-y divide-pitch-line rounded-lg border border-pitch-line bg-pitch-panel">
        {STAGES.map((stage) => (
          <details key={stage.tag} className="group open:bg-pitch-panel2/40">
            <summary className="flex cursor-pointer list-none items-center gap-4 px-5 py-4 marker:content-none">
              <span className="font-mono text-xs text-var-greendim">{stage.tag}</span>
              <span className="flex-1">
                <span className="block font-display text-base uppercase tracking-wide text-ink-100">
                  {stage.title}
                </span>
                <span className="block font-body text-xs text-ink-500">{stage.summary}</span>
              </span>
              <span className="font-mono text-ink-500 transition-transform group-open:rotate-45">
                +
              </span>
            </summary>
            <div className="space-y-3 px-5 pb-5 pl-[3.25rem] font-body text-sm leading-relaxed text-ink-300">
              {stage.body.map((para, i) => (
                <p key={i}>{para}</p>
              ))}
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
