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

/** Time left to the deadline, ticking; turns amber inside 24 hours and red
 *  inside 3. Hidden until it has a deadline in the future. */
export function Countdown({ deadline }: { deadline?: string | null }) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  if (!deadline || now === null) return null;
  const left = new Date(deadline).getTime() - now;
  if (!(left > 0)) return null;
  const { d, h, m, s } = parts(left);
  const tone = left < 3 * 3600e3 ? "border-risk/50 text-risk" : left < 24 * 3600e3 ? "border-warn/50 text-warn" : "border-line-strong text-ink-200";
  const text = d > 0 ? `${d}d ${h}h ${String(m).padStart(2, "0")}m` : `${h}h ${String(m).padStart(2, "0")}m ${String(s).padStart(2, "0")}s`;
  return (
    <span className={`pill tabular-nums ${tone}`} title={`Deadline ${new Date(deadline).toLocaleString()}`}>
      <span className="text-ink-400">Deadline</span> {text}
    </span>
  );
}
