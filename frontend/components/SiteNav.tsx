// File: SiteNav.tsx
// Path: var-ified-xi/frontend/components/SiteNav.tsx
//
// Sticky section nav with scroll-spy. The page is a long single column by
// design — the argument reads top to bottom — but that makes it hard to get
// back to the one section you actually came for. This tracks which section is
// on screen and lets you jump straight to any of them.

"use client";

import { useEffect, useState } from "react";

const LINKS = [
  { id: "week", label: "This week" },
  { id: "chips", label: "Chips" },
  { id: "league", label: "League" },
  { id: "squad", label: "Squad" },
  { id: "outlook", label: "Plan" },
  { id: "how", label: "How" },
  { id: "faq", label: "FAQ" },
];

export default function SiteNav() {
  const [active, setActive] = useState<string>("week");
  const [present, setPresent] = useState<string[]>([]);

  useEffect(() => {
    // Some sections only exist in transfer-plan mode, so the nav is built
    // from what's actually on the page rather than from the list above.
    const found = LINKS.filter((l) => document.getElementById(l.id)).map((l) => l.id);
    setPresent(found);

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      // Bias the band toward the upper half so the highlight changes when a
      // section reaches reading position, not when it first peeks in.
      { rootMargin: "-20% 0px -65% 0px", threshold: 0 }
    );

    found.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  if (present.length === 0) return null;

  return (
    <nav
      aria-label="Sections"
      className="sticky top-[57px] z-30 border-b border-pitch-line bg-pitch-night/90 backdrop-blur"
    >
      <div className="mx-auto max-w-5xl px-5">
        <ul className="-mx-1 flex gap-1 overflow-x-auto py-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {LINKS.filter((l) => present.includes(l.id)).map((l) => {
            const isActive = active === l.id;
            return (
              <li key={l.id}>
                <a
                  href={`#${l.id}`}
                  aria-current={isActive ? "true" : undefined}
                  className={`relative block whitespace-nowrap rounded-md px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.12em] transition-colors ${
                    isActive
                      ? "bg-var-green/10 text-var-green"
                      : "text-ink-400 hover:bg-pitch-panel hover:text-ink-200"
                  }`}
                >
                  {l.label}
                </a>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}
