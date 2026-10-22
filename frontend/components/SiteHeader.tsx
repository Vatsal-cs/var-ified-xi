// File: SiteHeader.tsx
// Path: var-ified-xi/frontend/components/SiteHeader.tsx
//
// The header and page nav are ONE sticky element, so nothing scrolls through a
// gap between them. One grid places every piece: on a phone the brand, the
// deadline and the theme switch share the top row and the nav scrolls under
// them, with the Run button pinned to that row's end (the nav leaves room for
// it); on a wide screen everything sits in a single row. Each piece exists
// once (the Run button polls, so it must not be mounted twice).

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { OptimizedTeam } from "@/lib/types";
import RefreshButton from "@/components/RefreshButton";
import { SHIRT_PATH } from "@/components/Shirt";
import { DeadlineChip, ThemeToggle } from "@/components/motion";

/** One page of the site, as the nav lists it (components/PageShell.tsx). */
export type NavPage = { href: string; label: string };

export default function SiteHeader({ team, pages }: { team: OptimizedTeam; pages: NavPage[] }) {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-base/85 backdrop-blur-md transition-colors duration-300">
      <div className="mx-auto grid max-w-6xl grid-cols-[1fr_auto_auto] items-center gap-x-2.5 gap-y-2 px-4 py-3 [grid-template-areas:'brand_chip_toggle'_'nav_nav_nav'] sm:px-6 md:grid-cols-[auto_1fr_auto_auto_auto] md:[grid-template-areas:'brand_nav_chip_refresh_toggle']">
        <Link href="/" className="flex items-center gap-2.5 [grid-area:brand]">
          <span className="grid h-8 w-8 flex-none place-items-center rounded-md bg-ink-100">
            <svg viewBox="0 0 120 120" className="h-7 w-7" aria-hidden>
              <path d={SHIRT_PATH} fill="rgb(var(--c-base))" />
              <text x="60" y="86" textAnchor="middle" className="font-kit" fontWeight="700" fontSize="40" fill="rgb(var(--c-ink-100))">
                XI
              </text>
            </svg>
          </span>
          <span className="whitespace-nowrap font-display text-[22px] font-extrabold uppercase leading-none tracking-[0.01em] text-ink-100 sm:text-[25px]">
            VAR<span className="text-gold">ified</span> XI
          </span>
        </Link>

        {pages.length > 0 && (
          <nav aria-label="Pages" className="min-w-0 pr-[126px] [grid-area:nav] md:ml-6 md:pr-0">
            <ul className="flex gap-5 overflow-x-auto [scrollbar-width:none] sm:gap-6 [&::-webkit-scrollbar]:hidden">
              {pages.map((l) => {
                const isActive = pathname === l.href;
                return (
                  <li key={l.href} className="relative">
                    <Link
                      href={l.href}
                      aria-current={isActive ? "page" : undefined}
                      className={`block whitespace-nowrap py-1.5 font-display text-[16px] font-bold uppercase tracking-[0.06em] transition-colors duration-200 ${
                        isActive ? "text-ink-100" : "text-ink-400 hover:text-ink-100"
                      }`}
                    >
                      {l.label}
                    </Link>
                    {/* The captain's armband marks where you are */}
                    {isActive && <span aria-hidden className="absolute inset-x-0 -bottom-[3px] h-[3px] rounded-full bg-gold" />}
                  </li>
                );
              })}
            </ul>
          </nav>
        )}

        <div className="[grid-area:chip]">
          <DeadlineChip deadline={team.deadline} gameweek={team.gameweek} />
        </div>
        <div className="z-[1] self-center justify-self-end [grid-area:nav] md:[grid-area:refresh]">
          <RefreshButton generatedAt={team.generated_at} />
        </div>
        <div className="[grid-area:toggle]">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
