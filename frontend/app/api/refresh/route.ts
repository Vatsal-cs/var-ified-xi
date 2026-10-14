// File: route.ts
// Path: var-ified-xi/frontend/app/api/refresh/route.ts
//
// The "Run now" button's server side. It starts the same GitHub Actions
// workflow the schedule runs (weekly.yml, with force=true), which runs the
// engine, commits the new optimized_team.json, and so redeploys the site.
//
// The GitHub token lives only here, on the server (Vercel env GITHUB_TOKEN:
// a fine-grained token with Actions read/write on this one repo). The site is
// public, so a click is rate-limited: one run at a time, a cooldown between
// manual runs, and a daily cap — each run costs ~6 Actions minutes and a
// deploy.

import team from "@/public/optimized_team.json";

export const dynamic = "force-dynamic";

const REPO = process.env.GITHUB_REPO ?? "Vatsal-cs/var-ified-xi";
const WORKFLOW = "weekly.yml";
const COOLDOWN_MIN = 10;
const DAILY_LIMIT = 6;
const ACTIVE = new Set(["queued", "in_progress", "waiting", "requested", "pending"]);

type Run = {
  status: string;
  conclusion: string | null;
  event: string;
  created_at: string;
  html_url: string;
};

function gh(path: string, init: RequestInit = {}) {
  return fetch(`https://api.github.com/repos/${REPO}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
      "X-GitHub-Api-Version": "2022-11-28",
      ...(init.headers ?? {}),
    },
  });
}

async function recentRuns(): Promise<Run[]> {
  const res = await gh(`/actions/workflows/${WORKFLOW}/runs?per_page=20`);
  if (!res.ok) throw new Error(`GitHub ${res.status}`);
  return (await res.json()).workflow_runs as Run[];
}

function summary(run: Run | undefined) {
  if (!run) return null;
  return {
    status: run.status,
    conclusion: run.conclusion,
    event: run.event,
    created_at: run.created_at,
    url: run.html_url,
  };
}

// The generated_at of the data THIS deployment serves. The button compares it
// with what the page showed to know when the new deploy is live.
const deployed = (team as { generated_at?: string }).generated_at ?? null;

export async function GET() {
  if (!process.env.GITHUB_TOKEN) {
    return Response.json({ configured: false, run: null, deployed });
  }
  try {
    const runs = await recentRuns();
    return Response.json({ configured: true, run: summary(runs[0]), deployed });
  } catch {
    return Response.json({ configured: true, run: null, deployed, error: "github" }, { status: 502 });
  }
}

export async function POST() {
  if (!process.env.GITHUB_TOKEN) {
    return Response.json({ error: "not_configured" }, { status: 503 });
  }

  let runs: Run[];
  try {
    runs = await recentRuns();
  } catch {
    return Response.json({ error: "github" }, { status: 502 });
  }

  const latest = runs[0];
  if (latest && ACTIVE.has(latest.status)) {
    return Response.json({ error: "running", run: summary(latest) }, { status: 409 });
  }

  const manual = runs.filter((r) => r.event === "workflow_dispatch");
  const now = Date.now();
  const lastManual = manual[0] ? new Date(manual[0].created_at).getTime() : 0;
  const waitMin = Math.ceil(COOLDOWN_MIN - (now - lastManual) / 60000);
  if (waitMin > 0) {
    return Response.json({ error: "cooldown", wait_min: waitMin }, { status: 429 });
  }

  const today = new Date().toISOString().slice(0, 10);
  if (manual.filter((r) => r.created_at.startsWith(today)).length >= DAILY_LIMIT) {
    return Response.json({ error: "daily_limit", limit: DAILY_LIMIT }, { status: 429 });
  }

  const res = await gh(`/actions/workflows/${WORKFLOW}/dispatches`, {
    method: "POST",
    body: JSON.stringify({ ref: "main", inputs: { force: "true" } }),
  });
  if (res.status !== 204) {
    return Response.json({ error: "github", status: res.status }, { status: 502 });
  }
  return Response.json({ started: true, at: new Date().toISOString() }, { status: 202 });
}
