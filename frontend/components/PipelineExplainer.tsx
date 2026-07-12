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
    summary: "An XGBoost regressor trained on this season's actual results.",
    body: [
      "A gradient-boosted decision tree model (400 trees, depth 4) is trained fresh on every historical gameweek row this season — literally: given a player's form going into a gameweek, what points did they actually score? The model learns that mapping directly from your league's real results, not a generic pre-trained model.",
      "It's validated on a held-out 15% slice of gameweeks it never trained on, so the reported accuracy reflects genuine unseen-data performance, not a model grading its own homework. Predictions for injured, suspended, or unlikely-to-play players are automatically dampened using FPL's own official status flags.",
    ],
  },
  {
    tag: "04",
    title: "Constraint Solver",
    summary: "A real optimizer, not a top-15-by-points list.",
    body: [
      "This is the part that actually separates this from a spreadsheet sort. A Mixed-Integer Linear Program (solved with PuLP/CBC) simultaneously decides three things at once: which 15 players fill the squad, which 11 of those start, and who wears the armband.",
      "It's bound by every real FPL rule: a hard £100.0m budget, an exact 2 goalkeeper / 5 defender / 5 midfielder / 3 forward squad split, a valid starting formation, and no more than 3 players from any one club. The objective function rewards the starting XI's predicted points at full weight, the bench at a small fraction, and adds a bonus for whichever player is made captain — so the solver is mathematically proven optimal for those constraints, not just \"pretty good.\"",
    ],
  },
  {
    tag: "05",
    title: "Decision",
    summary: "The confirmed squad, written out and shown above.",
    body: [
      "The solver's output — starting XI, bench, captain, and vice-captain — gets written to a single JSON file. This exact page reads that file directly. There's no live server making these picks on request; every player position and prediction above came from that one offline solve.",
      "Re-running the engine (weekly, ideally the day before your deadline) regenerates this file with fresh form data and a fresh solve.",
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
