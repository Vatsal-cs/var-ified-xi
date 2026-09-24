// File: SiteHeader.tsx
// Path: var-ified-xi/frontend/components/SiteHeader.tsx
//
// Header and section nav are ONE sticky element. They used to be two, with the
// nav pinned at a hardcoded top-[57px] guessed from the header's padding — so
// any change to the header's height opened a gap that page content scrolled
// through. Stacking them in a single sticky shell removes the guess entirely.

"use client";

import { useEffect, useState } from "react";
import type { OptimizedTeam } from "@/lib/types";

const LINKS = [
  { id: "week", label: "This week" },
  { id: "chips", label: "Chips" },
  { id: "league", label: "League" },
  { id: "squad", label: "Squad" },
  { id: "outlook", label: "Plan" },
  { id: "how", label: "How" },
  { id: "faq", label: "FAQ" },
];

function timeAgo(iso: string) {
  const then = new Date(iso).getTime();
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

export default function SiteHeader({ team }: { team: OptimizedTeam }) {
  const [active, setActive] = useState("week");
  const [present, setPresent] = useState<string[]>([]);

  useEffect(() => {
    // Built from what's on the page: fresh-squad mode has no plan or league.
    const found = LINKS.filter((l) => document.getElementById(l.id)).map((l) => l.id);
    setPresent(found);

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-25% 0px -60% 0px", threshold: 0 }
    );
    found.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  const visible = LINKS.filter((l) => present.includes(l.id));

  return (
    <header className="sticky top-0 z-50">
      {/* Opaque base under a blur layer. The old bar was bg/90 with no solid
          underneath, which let headings read straight through it. */}
      <div className="absolute inset-0 -z-10 bg-base/95 backdrop-blur-xl" />
      <div className="absolute inset-x-0 bottom-0 -z-10 h-px bg-brand-gradient opacity-30" />

      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3">
        <a href="#top" className="group flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-gradient font-display text-[13px] font-extrabold text-base shadow-brand">
            V
          </span>
          <span className="font-display text-[17px] font-extrabold tracking-tight text-ink-100">
            VAR<span className="text-gradient">ified</span> XI
          </span>
        </a>

        <div className="flex items-center gap-2.5 font-mono text-[10px]">
          <span className="pill hidden border-line-strong text-ink-300 sm:inline-flex">
            {team.mode === "transfer_plan" ? "Transfer plan" : "Fresh squad"}
          </span>
          <span className="pill border-brand-violet/40 bg-brand-soft text-ink-100">
            GW {team.gameweek ?? "—"}
          </span>
          <span className="hidden items-center gap-1.5 text-ink-400 md:inline-flex">
            <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-pts" />
            {timeAgo(team.generated_at)}
          </span>
        </div>
      </div>

      {visible.length > 0 && (
        <nav aria-label="Sections" className="border-t border-line">
          <div className="mx-auto max-w-6xl px-5">
            <ul className="flex gap-1 overflow-x-auto py-1.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              {visible.map((l) => {
                const isActive = active === l.id;
                return (
                  <li key={l.id}>
                    <a
                      href={`#${l.id}`}
                      aria-current={isActive ? "true" : undefined}
                      className={`relative block whitespace-nowrap rounded-lg px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.16em] transition-all duration-200 ${
                        isActive
                          ? "bg-brand-soft text-ink-100"
                          : "text-ink-400 hover:bg-white/[0.04] hover:text-ink-200"
                      }`}
                    >
                      {l.label}
                      {isActive && (
                        <span className="absolute inset-x-3 -bottom-[7px] h-[2px] rounded-full bg-brand-gradient" />
                      )}
                    </a>
                  </li>
                );
              })}
            </ul>
          </div>
        </nav>
      )}
    </header>
  );
}
