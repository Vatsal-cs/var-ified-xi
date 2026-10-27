// File: SiteHeader.tsx
// Path: var-ified-xi/frontend/components/SiteHeader.tsx
//
// The header and page nav are ONE sticky element, so nothing scrolls through a
// gap between them. One grid places every piece: on a phone the brand and the
// deadline share the top row and the nav scrolls under them, with the Run
// button and the theme switch pinned to that row's end (the nav leaves room
// for them); on a wide screen everything sits in a single row. Each piece
// exists once (the Run button polls, so it must not be mounted twice).

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { OptimizedTeam } from "@/lib/types";
import RefreshButton from "@/components/RefreshButton";
import LogoMark from "@/components/Logo";
import { DeadlineChip, ThemeToggle } from "@/components/motion";

/** One page of the site, as the nav lists it (components/PageShell.tsx). */
export type NavPage = { href: string; label: string };

export default function SiteHeader({ team, pages }: { team: OptimizedTeam; pages: NavPage[] }) {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-base/95 backdrop-blur-md transition-colors duration-300">
      <div className="mx-auto grid max-w-6xl grid-cols-[1fr_auto] items-center gap-x-2.5 gap-y-2.5 px-4 py-3 [grid-template-areas:'brand_chip'_'nav_nav'] sm:px-6 md:grid-cols-[auto_1fr_auto_auto] md:gap-x-3 md:py-3.5 md:[grid-template-areas:'brand_nav_chip_actions']">
        <Link href="/" aria-label="VAR-ified XI, this week" className="group flex items-center gap-2.5 [grid-area:brand]">
          <LogoMark className="h-8 w-8 flex-none drop-shadow-[0_3px_6px_rgba(0,0,0,0.3)] transition-transform duration-300 group-hover:-rotate-6 sm:h-10 sm:w-10" />
          <span className="leading-none">
            <span className="block whitespace-nowrap font-display text-[20px] font-black uppercase tracking-[0.02em] text-ink-100 sm:text-[25px]">
              VAR-ified <span className="text-gold">XI</span>
            </span>
            <span className="mt-1 hidden text-[9.5px] font-semibold uppercase tracking-[0.3em] text-ink-400 sm:block">
              FPL, reviewed
            </span>
          </span>
        </Link>

        {pages.length > 0 && (
          <nav aria-label="Pages" className="min-w-0 pr-[88px] [grid-area:nav] md:ml-4 md:border-l md:border-line md:pl-6 md:pr-0">
            <ul className="flex gap-5 overflow-x-auto [scrollbar-width:none] sm:gap-6 [&::-webkit-scrollbar]:hidden">
              {pages.map((l) => {
                const isActive = pathname === l.href;
                return (
                  <li key={l.href} className="relative">
                    <Link
                      href={l.href}
                      aria-current={isActive ? "page" : undefined}
                      className={`group/tab relative block whitespace-nowrap py-1.5 font-display text-[16px] font-bold uppercase tracking-[0.06em] transition-colors duration-200 ${
                        isActive ? "text-ink-100" : "text-ink-400 hover:text-ink-100"
                      }`}
                    >
                      {l.label}
                      {/* The captain's armband marks where you are; hovering draws one in */}
                      <span
                        aria-hidden
                        className={`absolute inset-x-0 -bottom-[3px] h-[3px] origin-left rounded-full transition-transform duration-300 ${
                          isActive ? "scale-x-100 bg-gold" : "scale-x-0 bg-ink-400 group-hover/tab:scale-x-100"
                        }`}
                      />
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        )}

        <div className="[grid-area:chip]">
          <DeadlineChip deadline={team.deadline} gameweek={team.gameweek} />
        </div>
        {/* On a phone these sit at the end of the nav row, which leaves them room */}
        <div className="z-[1] flex items-center gap-2 self-center justify-self-end [grid-area:nav] md:[grid-area:actions]">
          <RefreshButton generatedAt={team.generated_at} />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
