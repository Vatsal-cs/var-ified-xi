// File: RefreshButton.tsx
// Path: var-ified-xi/frontend/components/RefreshButton.tsx
//
// "Run now": asks /api/refresh to start the engine on the latest FPL data,
// shows the run's progress, and reloads the page once the redeployed site
// serves the new numbers (~6 minutes end to end). The label doubles as the
// status line, so it fits the header on a phone.
//
// Without a GitHub token on the server it becomes "Run on GitHub": a link to
// the workflow's page, where "Run workflow" starts the same run. The page then
// can't see the run itself, only the redeploy, so it waits for that.

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Phase = "idle" | "starting" | "running" | "publishing" | "waiting";

type Status = {
  configured: boolean;
  deployed: string | null;
  workflow_url?: string;
  run: { status: string; conclusion: string | null; created_at: string } | null;
};

const ACTIVE = new Set(["queued", "in_progress", "waiting", "requested", "pending"]);
const POLL_MS = 10_000;
// A finished run that changed nothing never redeploys; stop waiting after this.
const PUBLISH_TIMEOUT_MS = 5 * 60_000;
// Run started by hand on GitHub: allow for getting to the button, the run
// (~6 min) and the deploy.
const WAIT_TIMEOUT_MS = 15 * 60_000;

const ERRORS: Record<string, string> = {
  daily_limit: "Daily limit hit",
  github: "Couldn't start",
};

export default function RefreshButton({ generatedAt }: { generatedAt: string }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [note, setNote] = useState("");
  const [since, setSince] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const [manualUrl, setManualUrl] = useState<string | null>(null);
  const phaseRef = useRef<Phase>("idle");
  const dispatchedAt = useRef(0);
  const phaseSince = useRef(0);

  const go = useCallback((p: Phase) => {
    if (phaseRef.current !== p) phaseSince.current = Date.now();
    phaseRef.current = p;
    setPhase(p);
  }, []);

  const flash = useCallback((text: string) => {
    setNote(text);
    setTimeout(() => setNote(""), 6000);
  }, []);

  const check = useCallback(async () => {
    let s: Status;
    try {
      s = await fetch("/api/refresh", { cache: "no-store" }).then((r) => r.json());
    } catch {
      return;
    }
    if (s.deployed && Date.parse(s.deployed) > Date.parse(generatedAt)) {
      window.location.reload();
      return;
    }
    setManualUrl(s.configured ? null : s.workflow_url ?? null);

    const current = phaseRef.current;
    const waited = Date.now() - phaseSince.current;
    if (current === "waiting") {
      if (waited > WAIT_TIMEOUT_MS) {
        go("idle");
        flash("No new data yet");
      }
      return;
    }

    const run = s.run;
    if (!run) return;
    const created = Date.parse(run.created_at);
    if (ACTIVE.has(run.status)) {
      setSince(created);
      go("running");
      return;
    }
    const ours = current === "running" || (current === "starting" && created >= dispatchedAt.current - 60_000);
    if (ours) {
      if (run.conclusion === "success") {
        go("publishing");
      } else {
        go("idle");
        flash("Run failed");
      }
    } else if (current === "publishing" && waited > PUBLISH_TIMEOUT_MS) {
      go("idle");
      flash("Up to date");
    }
  }, [generatedAt, go, flash]);

  // Pick up a run already in progress (another tab, the schedule) on load.
  useEffect(() => {
    check();
  }, [check]);

  useEffect(() => {
    if (phase === "idle") return;
    const poll = setInterval(check, POLL_MS);
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      clearInterval(poll);
      clearInterval(tick);
    };
  }, [phase, check]);

  async function start() {
    if (phase !== "idle") return;
    setNote("");
    dispatchedAt.current = Date.now();
    go("starting");
    let res: Response;
    let body: { error?: string; wait_min?: number; run?: { created_at: string } } = {};
    try {
      res = await fetch("/api/refresh", { method: "POST" });
      body = await res.json().catch(() => ({}));
    } catch {
      go("idle");
      flash("Couldn't start");
      return;
    }
    if (res.status === 202) {
      setSince(Date.now());
      return; // polling takes it from here
    }
    if (body.error === "running" && body.run) {
      setSince(Date.parse(body.run.created_at));
      go("running");
      return;
    }
    go("idle");
    if (body.error === "not_configured") {
      check(); // switches the button to its GitHub link
      return;
    }
    flash(body.error === "cooldown" ? `Wait ${body.wait_min}m` : ERRORS[body.error ?? ""] ?? "Couldn't start");
  }

  const mins = Math.max(0, Math.floor((now - since) / 60000));
  const waitMins = Math.max(0, Math.floor((now - phaseSince.current) / 60000));
  const label =
    note ||
    {
      idle: manualUrl ? "Run on GitHub" : "Run now",
      starting: "Starting…",
      running: `Running · ${mins}m`,
      publishing: "Publishing…",
      waiting: `Waiting · ${waitMins}m`,
    }[phase];
  const busy = phase !== "idle";
  const className = `pill transition-colors ${
    busy
      ? "cursor-default border-pts/40 text-pts"
      : "border-line-strong text-ink-200 hover:border-gold/50 hover:text-gold"
  } h-9 justify-center px-2.5 md:px-3`;
  const icon = busy ? (
    <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-pts" />
  ) : (
    <svg aria-hidden viewBox="0 0 16 16" className="h-3.5 w-3.5 fill-none stroke-current md:h-2.5 md:w-2.5" strokeWidth="1.8">
      <path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 2.5v3h-3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );

  // No token: a real link (a popup opened after an await gets blocked), and
  // this tab waits for the redeploy while the run happens on GitHub.
  if (manualUrl && !busy) {
    return (
      <a
        href={manualUrl}
        target="_blank"
        rel="noopener noreferrer"
        onClick={() => go("waiting")}
        aria-live="polite"
        title='Opens the workflow on GitHub: press "Run workflow" there. This page reloads itself when the new data is live, about 7 minutes later.'
        className={className}
        aria-label={label}
      >
        {icon}
        <span className="hidden md:inline">{label}</span>
      </a>
    );
  }

  return (
    <button
      type="button"
      onClick={start}
      disabled={busy}
      aria-live="polite"
      title="Run the model on the latest FPL data. Takes about 6 minutes, then the page reloads."
      className={className}
      aria-label={label}
    >
      {icon}
      {/* On a phone the button is just its icon, unless a run is under way */}
      <span className={busy ? "" : "hidden md:inline"}>{label}</span>
    </button>
  );
}
