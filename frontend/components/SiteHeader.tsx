// File: SiteHeader.tsx
// Path: var-ified-xi/frontend/components/SiteHeader.tsx
//
// Header and page nav are ONE sticky element. They used to be two, with the
// nav pinned at a hardcoded top-[57px] guessed from the header's padding — so
// any change to the header's height opened a gap that page content scrolled
// through. Stacking them in a single sticky shell removes the guess entirely.

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { OptimizedTeam } from "@/lib/types";
import RefreshButton from "@/components/RefreshButton";
import VarMark from "@/components/VarMark";
import { DeadlineBar } from "@/components/motion";

/** One page of the site, as the nav lists it (components/PageShell.tsx). */
export type NavPage = { href: string; label: string };

function timeAgo(iso: string) {
  const then = new Date(iso).getTime();
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

export default function SiteHeader({
  team,
  pages,
}: {
  team: OptimizedTeam;
  pages: NavPage[];
}) {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50">
      {/* Opaque base under a blur layer. The old bar was bg/90 with no solid
          underneath, which let headings read straight through it. */}
      <div className="absolute inset-0 -z-10 border-b border-line bg-base" />

      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3">
        <Link href="/" className="flex items-center gap-2.5">
          <VarMark />
          <span className="font-display text-[19px] leading-none tracking-[-0.01em] text-ink-100">
            VAR<span className="italic text-gold">ified</span> XI
          </span>
        </Link>

        <div className="flex items-center gap-2.5 font-mono text-[10px]">
          <span className="pill hidden border-line-strong text-ink-300 sm:inline-flex">
            {team.mode === "transfer_plan" ? "Transfer plan" : "Fresh squad"}
          </span>
          <span className="pill border-gold/35 text-gold">
            GW {team.gameweek ?? "—"}
          </span>
          <span className="hidden items-center gap-1.5 text-ink-400 md:inline-flex">
            <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-pts" />
            {timeAgo(team.generated_at)}
          </span>
          <RefreshButton generatedAt={team.generated_at} />
        </div>
      </div>

      <DeadlineBar deadline={team.deadline} gameweek={team.gameweek} />

      {pages.length > 0 && (
        <nav aria-label="Pages" className="border-t border-line">
          <div className="mx-auto max-w-6xl px-5">
            <ul className="flex gap-1 overflow-x-auto py-1.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              {pages.map((l) => {
                const isActive = pathname === l.href;
                return (
                  <li key={l.href}>
                    <Link
                      href={l.href}
                      aria-current={isActive ? "page" : undefined}
                      className={`relative block whitespace-nowrap rounded-[2px] px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.16em] transition-all duration-200 ${
                        isActive
                          ? "text-gold"
                          : "text-ink-400 hover:bg-white/[0.04] hover:text-ink-200"
                      }`}
                    >
                      {l.label}
                      {isActive && (
                        <span className="absolute inset-x-3 -bottom-[7px] h-[2px] bg-gradient-to-r from-gold via-violet to-sky" />
                      )}
                    </Link>
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
