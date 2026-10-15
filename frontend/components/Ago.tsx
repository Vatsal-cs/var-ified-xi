// File: Ago.tsx
// Path: var-ified-xi/frontend/components/Ago.tsx
//
// "3h ago", worked out in the browser. The page is built once per deploy, so
// a relative time computed at build would freeze; this one stays true.

"use client";

import { useEffect, useState } from "react";

function rel(iso: string) {
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 60) return `${mins}m ago`;
  const h = Math.round(mins / 60);
  return h < 48 ? `${h}h ago` : `${Math.round(h / 24)}d ago`;
}

export default function Ago({ iso }: { iso: string }) {
  const [text, setText] = useState<string | null>(null);
  useEffect(() => {
    setText(rel(iso));
    const t = setInterval(() => setText(rel(iso)), 60_000);
    return () => clearInterval(t);
  }, [iso]);
  return <time dateTime={iso}>{text ?? iso.slice(0, 16).replace("T", " ") + " UTC"}</time>;
}
