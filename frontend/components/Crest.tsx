// File: Crest.tsx
// Path: var-ified-xi/frontend/components/Crest.tsx
//
// A club's crest, sized by the className it's given. Falls back from the SVG
// to the PNG to the club's kit colours drawn as a disc, so a missing image or
// a club with no code still shows something that says which club it is.

"use client";

import { useState } from "react";
import { crestUrls, kitFor, needsOutline } from "@/lib/teams";

export default function Crest({ team, className = "" }: { team: string | undefined; className?: string }) {
  const urls = crestUrls(team);
  const [tried, setTried] = useState(0);

  if (tried >= urls.length) {
    const kit = kitFor(team);
    return (
      <svg viewBox="0 0 40 40" className={className} role="img" aria-label={team ?? "club"}>
        <circle
          cx="20"
          cy="20"
          r="18.5"
          fill={kit.shirt}
          stroke={needsOutline(kit) ? "rgba(0,0,0,0.45)" : "none"}
          strokeWidth="1.5"
        />
        <text x="20" y="23.6" textAnchor="middle" fontSize="10" fontWeight="700" letterSpacing="0.5" fill={kit.trim}>
          {kit.abbr}
        </text>
      </svg>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element -- a remote SVG at a few dozen pixels; nothing to optimise
    <img
      src={urls[tried]}
      alt={`${team} crest`}
      className={`object-contain ${className}`}
      draggable={false}
      decoding="async"
      onError={() => setTried((t) => t + 1)}
    />
  );
}
