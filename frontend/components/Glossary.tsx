// File: Glossary.tsx
// Path: var-ified-xi/frontend/components/Glossary.tsx

const TERMS: { term: string; def: string }[] = [
  {
    term: "Predicted points (xP)",
    def: "The XGBoost model's estimate of how many points a player will score in the upcoming gameweek, based on their recent form and fixture.",
  },
  {
    term: "MILP",
    def: "Mixed-Integer Linear Program — a mathematical optimization method that finds the provably best combination of yes/no decisions (which 15 players, who starts, who captains) under a set of hard rules, rather than approximating with sorting or heuristics.",
  },
  {
    term: "Rolling form",
    def: "A player's average performance over their last 3 or 5 gameweeks, recalculated every run so the model always reacts to recent form rather than season-long averages.",
  },
  {
    term: "MAE (validation)",
    def: "Mean Absolute Error — on average, how many points off the model's predictions were on gameweeks it never trained on. Lower is better.",
  },
  {
    term: "Captain multiplier",
    def: "FPL rule: your captain's points are doubled. The solver treats this as a real bonus in its objective function when choosing who to captain, not an afterthought applied later.",
  },
  {
    term: "Club limit",
    def: "FPL rule: no more than 3 players from any single Premier League club are allowed in your 15-man squad.",
  },
];

export default function Glossary() {
  return (
    <section aria-labelledby="glossary-heading" className="mx-auto max-w-3xl">
      <h2 id="glossary-heading" className="mb-4 font-display text-xl uppercase tracking-tight text-ink-100">
        Terms used on this page
      </h2>
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {TERMS.map((t) => (
          <div key={t.term} className="rounded-md border border-pitch-line bg-pitch-panel p-4">
            <dt className="font-mono text-xs uppercase tracking-wide text-var-green">{t.term}</dt>
            <dd className="mt-1.5 font-body text-sm leading-relaxed text-ink-300">{t.def}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
