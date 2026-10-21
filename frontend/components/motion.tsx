// File: motion.tsx
// Path: var-ified-xi/frontend/components/motion.tsx
//
// The page's small amount of motion, all client-side and all optional:
// sections that arrive as they scroll in, numbers that count up, a soft
// spotlight on the lead panel, and the deadline countdown. Everything
// renders its final state without JavaScript and respects reduced motion.

"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

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

/** A panel with a soft gold spotlight that follows the pointer. */
export function Spotlight({
  children,
  className = "",
  id,
  style,
}: {
  children: ReactNode;
  className?: string;
  id?: string;
  style?: CSSProperties;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const onMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--mx", `${e.clientX - r.left}px`);
    el.style.setProperty("--my", `${e.clientY - r.top}px`);
  };
  return (
    <div ref={ref} id={id} onPointerMove={onMove} className={className} style={style}>
      <span aria-hidden className="spotlight pointer-events-none absolute inset-0" />
      {children}
    </div>
  );
}

function parts(ms: number) {
  const s = Math.max(0, Math.floor(ms / 1000));
  return { d: Math.floor(s / 86400), h: Math.floor((s % 86400) / 3600), m: Math.floor((s % 3600) / 60), s: s % 60 };
}

const WEEK = 7 * 86400e3;

const TONES = {
  calm: { text: "text-gold", dot: "bg-gold", bar: "from-gold/40 via-gold/80 to-gold" },
  warn: { text: "text-warn", dot: "bg-warn", bar: "from-gold/60 via-warn/80 to-warn" },
  risk: { text: "text-risk", dot: "bg-risk", bar: "from-warn/70 via-risk/80 to-risk" },
};

const pad = (n: number) => String(n).padStart(2, "0");

/** The deadline as a strip across the header, on every screen size: the
 *  gameweek, its time where you are, and the time left down to the second.
 *  Gold, amber inside 24 hours, red and pulsing inside 3; a hairline under
 *  it fills as the week runs out. Renders its frame on the server and the
 *  clock once mounted, so the local time never mismatches. */
export function DeadlineBar({ deadline, gameweek }: { deadline?: string | null; gameweek?: number | null }) {
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
  const tone = left === null || passed ? TONES.calm : left < 3 * 3600e3 ? TONES.risk : left < 24 * 3600e3 ? TONES.warn : TONES.calm;
  const { d, h, m, s } = parts(left ?? 0);
  const segs: [number, string][] = d > 0 ? [[d, "d"], [h, "h"], [m, "m"], [s, "s"]] : [[h, "h"], [m, "m"], [s, "s"]];
  const filled = left === null ? 0 : Math.min(1, Math.max(0, 1 - left / WEEK)) * 100;

  return (
    <div className="relative border-t border-line" role="timer" aria-label={`Gameweek ${gameweek ?? ""} deadline`}>
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-5 py-2">
        <span className="flex min-w-0 items-center gap-2 font-mono text-[10px]">
          <span
            className={`h-1.5 w-1.5 flex-none rounded-full ${tone.dot} ${tone.text} ${tone === TONES.risk ? "animate-pulseDot" : ""}`}
            style={{ boxShadow: "0 0 10px currentColor" }}
          />
          <span className="whitespace-nowrap uppercase tracking-[0.18em] text-ink-200">
            GW {gameweek ?? "—"} deadline
          </span>
          {now !== null && (
            <span className="truncate text-ink-500">
              <span className="sm:hidden">
                {at.toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" })}
              </span>
              <span className="hidden sm:inline">
                {at.toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short" })} &middot;{" "}
                {at.toLocaleString(undefined, { hour: "numeric", minute: "2-digit" })}
              </span>
            </span>
          )}
        </span>

        <span className="ml-auto flex flex-none items-baseline font-mono tabular-nums">
          {left === null ? (
            <span className="text-[18px] leading-none text-ink-500 sm:text-[21px]">--:--</span>
          ) : passed ? (
            <span className="text-[11px] uppercase tracking-[0.16em] text-ink-400">Passed &middot; plan updates soon</span>
          ) : (
            segs.map(([v, unit]) => (
              <span key={unit} className="flex items-baseline">
                <span
                  key={unit === "s" ? v : undefined}
                  className={`inline-block text-[18px] font-medium leading-none sm:text-[21px] ${tone.text} ${
                    unit === "s" ? "animate-tick" : ""
                  }`}
                >
                  {pad(v)}
                </span>
                <span className={`ml-[2px] text-[9px] uppercase text-ink-500 ${unit === "s" ? "" : "mr-[7px]"}`}>{unit}</span>
              </span>
            ))
          )}
        </span>
      </div>
      <div aria-hidden className="absolute inset-x-0 bottom-0 h-[2px] bg-white/[0.04]">
        <div
          className={`h-full bg-gradient-to-r ${tone.bar} transition-[width] duration-1000 ease-linear`}
          style={{ width: `${filled}%`, boxShadow: "0 0 8px rgba(224,166,74,0.45)" }}
        />
      </div>
    </div>
  );
}
