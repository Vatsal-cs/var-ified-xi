// File: motion.tsx
// Path: var-ified-xi/frontend/components/motion.tsx
//
// The page's small amount of motion, all client-side and all optional:
// sections that arrive as they scroll in, numbers that count up, the deadline
// chip and the light/dark switch. Everything renders its final state without
// JavaScript and respects reduced motion.

"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

const reduced = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Fades and lifts its children in the first time they scroll into view. */
export function Reveal({ children, className = "" }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    document.documentElement.classList.add("js-reveal");
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add("is-in");
            io.unobserve(e.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={ref} className={`reveal ${className}`}>
      {children}
    </div>
  );
}

/** A number that counts up to its value once, on first render. */
export function CountUp({ value, decimals = 1, duration = 900 }: { value: number; decimals?: number; duration?: number }) {
  const [shown, setShown] = useState(value);
  useEffect(() => {
    if (reduced()) return;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(value * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    setShown(0);
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return <>{shown.toFixed(decimals)}</>;
}

function parts(ms: number) {
  const s = Math.max(0, Math.floor(ms / 1000));
  return { d: Math.floor(s / 86400), h: Math.floor((s % 86400) / 3600), m: Math.floor((s % 3600) / 60), s: s % 60 };
}

const pad = (n: number) => String(n).padStart(2, "0");

/** The deadline as a chip in the header, on every screen size: the gameweek
 *  and the time left down to the second. Calm until the last day, amber
 *  inside 24 hours, red and pulsing inside 3. Renders its frame on the server
 *  and the clock once mounted, so it never mismatches. */
export function DeadlineChip({ deadline, gameweek }: { deadline?: string | null; gameweek?: number | null }) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  if (!deadline) return null;
  const at = new Date(deadline);
  const left = now === null ? null : at.getTime() - now;
  const passed = left !== null && left <= 0;
  const urgent = left !== null && left > 0 && left < 3 * 3600e3;
  const soon = left !== null && left > 0 && left < 24 * 3600e3;
  const { d, h, m, s } = parts(left ?? 0);
  const dot = urgent ? "bg-risk animate-pulseDot" : soon ? "bg-warn" : "bg-pts animate-pulseDot";
  const tone = urgent ? "text-risk" : soon ? "text-warn" : "text-ink-100";

  return (
    <div
      role="timer"
      aria-label={`Gameweek ${gameweek ?? ""} deadline`}
      title={now === null ? undefined : `Deadline ${at.toLocaleString(undefined, { weekday: "long", hour: "numeric", minute: "2-digit" })}`}
      className="flex items-center gap-2 rounded-xl border border-line bg-surface px-2.5 py-1.5 text-[13px] text-ink-400 shadow-panel sm:px-3"
    >
      <span className={`h-[7px] w-[7px] flex-none rounded-full ${dot}`} />
      <span className="hidden whitespace-nowrap sm:inline">GW {gameweek ?? "—"} deadline</span>
      {left === null ? (
        <b className="font-semibold tabular-nums text-ink-300">—</b>
      ) : passed ? (
        <b className="whitespace-nowrap font-medium text-ink-300">Passed &middot; updating soon</b>
      ) : (
        <b className={`whitespace-nowrap font-semibold tabular-nums ${tone}`}>
          {d > 0 && `${d}d `}
          {h}h {pad(m)}m{" "}
          <span className="text-gold">
            <span key={s} className="inline-block animate-tick">
              {pad(s)}
            </span>
            s
          </span>
        </b>
      )}
    </div>
  );
}

/** Light or dark. Starts from whatever the page was painted in (the script in
 *  app/layout.tsx), and remembers the visitor's choice. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark" | null>(null);
  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
  }, []);
  const flip = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("vx-theme", next);
    } catch {
      /* private mode: the choice just isn't remembered */
    }
    setTheme(next);
  };
  return (
    <button
      type="button"
      onClick={flip}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      className="grid h-9 w-9 flex-none place-items-center rounded-xl border border-line bg-surface text-ink-100 shadow-panel transition-colors hover:border-line-strong"
    >
      {theme === "dark" ? (
        <svg viewBox="0 0 24 24" className="h-[17px] w-[17px]" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="h-[17px] w-[17px]" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      )}
    </button>
  );
}
