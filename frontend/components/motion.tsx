// File: motion.tsx
// Path: var-ified-xi/frontend/components/motion.tsx
//
// The page's small amount of motion, all client-side and all optional:
// sections that arrive as they scroll in, shirts that lean towards the
// pointer, numbers that count up, the deadline chip and the light/dark switch. Everything renders its final state without
// JavaScript and respects reduced motion.

"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

const reduced = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Fades and lifts its children in the first time they scroll into view.
 *  Any animation inside (shirts being hung, bars filling) waits until then. */
export function Reveal({ children, className = "" }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    document.documentElement.classList.add("js-reveal");
    (window as unknown as { __vxReveal?: boolean }).__vxReveal = true;
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

/** Holds every animation inside it — shirts swinging onto their pegs, the
 *  armband going on, bars filling — until it scrolls into view, then plays
 *  them from the start. Unlike <Reveal> it doesn't fade the block itself.
 *  The paused state is CSS (globals.css), so without JavaScript nothing waits. */
export function OnView({ children, className = "" }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    document.documentElement.classList.add("js-reveal");
    (window as unknown as { __vxReveal?: boolean }).__vxReveal = true;
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
      { rootMargin: "0px 0px -6% 0px", threshold: 0.08 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={ref} className={`on-view ${className}`}>
      {children}
    </div>
  );
}

/** Leans its contents towards the pointer, a few degrees in 3D, on a device
 *  with a mouse. Touch screens and reduced motion get it still. */
export function Tilt({ children, max = 8, className = "" }: { children: ReactNode; max?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || reduced() || !window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    let raf = 0;
    const move = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        el.style.transition = "transform 0.15s ease-out";
        el.style.transform = `perspective(900px) rotateX(${(-y * 2 * max).toFixed(2)}deg) rotateY(${(x * 2 * max).toFixed(2)}deg)`;
      });
    };
    const leave = () => {
      cancelAnimationFrame(raf);
      el.style.transition = "transform 0.7s cubic-bezier(0.22, 1, 0.36, 1)";
      el.style.transform = "";
    };
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerleave", leave);
    return () => {
      cancelAnimationFrame(raf);
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerleave", leave);
    };
  }, [max]);
  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}

/** A damped spring: pulled towards its target, carrying its speed, so it
 *  settles with a little overshoot instead of easing in a straight line. */
type Spring = { x: number; v: number; target: number };
const STIFFNESS = 110;
const DAMPING = 14; // under the critical 21, so it overshoots once, slightly
function step(s: Spring, dt: number) {
  s.v += (STIFFNESS * (s.target - s.x) - DAMPING * s.v) * dt;
  s.x += s.v * dt;
}
const settled = (s: Spring) => Math.abs(s.target - s.x) < 0.01 && Math.abs(s.v) < 0.01;

/** A 3D stage you can look round. Writes --orbit-tilt (how far the stage is
 *  tipped back, in degrees) and --orbit-spin (how far it's turned) on its
 *  element, for the children to use in their transforms. With a mouse it
 *  leans towards the pointer; on any device it can be dragged round, and on
 *  letting go it springs back. As it scrolls into view the camera cranes
 *  down from overhead to its resting angle. Reduced motion gets it still,
 *  at rest. */
export function Orbit({
  children,
  className = "",
  rest = 46,
  crane = 16,
  lean = 7,
  drag = 26,
}: {
  children: ReactNode;
  className?: string;
  /** The resting tilt, in degrees. */
  rest?: number;
  /** How much flatter it starts, before it has scrolled into view. */
  crane?: number;
  /** How far it leans towards the pointer, in degrees. */
  lean?: number;
  /** How far a drag can turn it, in degrees. */
  drag?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const write = (tilt: number, spin: number) => {
      el.style.setProperty("--orbit-tilt", `${tilt.toFixed(2)}deg`);
      el.style.setProperty("--orbit-spin", `${spin.toFixed(2)}deg`);
    };
    write(rest, 0);
    if (reduced()) return;

    const tilt: Spring = { x: rest - crane, v: 0, target: rest - crane };
    const spin: Spring = { x: 0, v: 0, target: 0 };
    let raf = 0;
    let last = 0;
    const tick = (now: number) => {
      const dt = Math.min(0.032, (now - last) / 1000 || 0.016);
      last = now;
      step(tilt, dt);
      step(spin, dt);
      write(tilt.x, spin.x);
      raf = settled(tilt) && settled(spin) ? 0 : requestAnimationFrame(tick);
    };
    const kick = () => {
      if (!raf) {
        last = performance.now();
        raf = requestAnimationFrame(tick);
      }
    };

    // The camera cranes down as the stage comes up the screen.
    let craned = 0;
    const onScroll = () => {
      const r = el.getBoundingClientRect();
      const vh = window.innerHeight;
      craned = Math.min(1, Math.max(0, (vh - r.top) / (vh * 0.7)));
      tilt.target = rest - crane * (1 - craned) + leanTilt;
      kick();
    };

    // Leaning towards the pointer, on a device with a mouse.
    let leanTilt = 0;
    const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    const onMove = (e: PointerEvent) => {
      if (dragging) return;
      const r = el.getBoundingClientRect();
      const nx = Math.max(-1, Math.min(1, ((e.clientX - r.left) / r.width - 0.5) * 2));
      const ny = Math.max(-1, Math.min(1, ((e.clientY - r.top) / r.height - 0.5) * 2));
      spin.target = nx * lean;
      leanTilt = ny * lean * 0.6;
      tilt.target = rest - crane * (1 - craned) + leanTilt;
      kick();
    };
    const onLeave = () => {
      if (dragging) return;
      spin.target = 0;
      leanTilt = 0;
      tilt.target = rest - crane * (1 - craned);
      kick();
    };

    // Dragging it round. Sideways only on a touch screen, so the page still
    // scrolls; a drag that moved doesn't count as a tap on what's under it.
    let dragging = false;
    let moved = false;
    let startX = 0;
    let startSpin = 0;
    const onDown = (e: PointerEvent) => {
      dragging = true;
      moved = false;
      startX = e.clientX;
      startSpin = spin.x;
    };
    const onDragMove = (e: PointerEvent) => {
      if (!dragging) return;
      const dx = e.clientX - startX;
      if (Math.abs(dx) > 6) moved = true;
      if (!moved) return;
      const r = el.getBoundingClientRect();
      spin.target = Math.max(-drag, Math.min(drag, startSpin + (dx / r.width) * drag * 2.2));
      kick();
    };
    const onUp = () => {
      if (!dragging) return;
      dragging = false;
      if (moved) {
        spin.target = 0; // let go: it springs back past the middle and settles
        kick();
      }
    };
    const onClick = (e: MouseEvent) => {
      if (moved) {
        e.stopPropagation();
        e.preventDefault();
        moved = false;
      }
    };

    onScroll();
    write(tilt.x, spin.x);
    kick();
    window.addEventListener("scroll", onScroll, { passive: true });
    if (fine) {
      el.addEventListener("pointermove", onMove);
      el.addEventListener("pointerleave", onLeave);
    }
    el.addEventListener("pointerdown", onDown);
    window.addEventListener("pointermove", onDragMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
    el.addEventListener("click", onClick, true);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onScroll);
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
      el.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointermove", onDragMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
      el.removeEventListener("click", onClick, true);
    };
  }, [rest, crane, lean, drag]);
  return (
    <div ref={ref} className={`touch-pan-y select-none ${className}`} style={{ ["--orbit-tilt" as string]: `${rest}deg`, ["--orbit-spin" as string]: "0deg" }}>
      {children}
    </div>
  );
}

/** Follows the pointer across the whole page, on a spring, and writes where
 *  it is as --px and --py (-1 to 1 from the middle of the screen) on the
 *  root, so backgrounds can shift with it in layers, nearer layers more.
 *  Mouse only; touch and reduced motion leave them at 0. */
export function PointerDepth() {
  useEffect(() => {
    if (reduced() || !window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    const root = document.documentElement;
    const px: Spring = { x: 0, v: 0, target: 0 };
    const py: Spring = { x: 0, v: 0, target: 0 };
    let raf = 0;
    let last = 0;
    const tick = (now: number) => {
      const dt = Math.min(0.032, (now - last) / 1000 || 0.016);
      last = now;
      step(px, dt);
      step(py, dt);
      root.style.setProperty("--px", px.x.toFixed(4));
      root.style.setProperty("--py", py.x.toFixed(4));
      raf = settled(px) && settled(py) ? 0 : requestAnimationFrame(tick);
    };
    const onMove = (e: PointerEvent) => {
      px.target = (e.clientX / window.innerWidth - 0.5) * 2;
      py.target = (e.clientY / window.innerHeight - 0.5) * 2;
      if (!raf) {
        last = performance.now();
        raf = requestAnimationFrame(tick);
      }
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onMove);
    };
  }, []);
  return null;
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

/** The deadline on the fourth official's board: a black board, the
 *  gameweek on a red panel, the time left in lit digits — green, amber inside
 *  24 hours, red inside 3. Dark in both themes, because the real one is.
 *  Renders its frame on the server and the clock once mounted. */
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
  const lit = urgent ? "#FF5A4A" : soon ? "#FFC247" : "#5BE38A";

  return (
    <div
      role="timer"
      aria-label={`Gameweek ${gameweek ?? ""} deadline`}
      title={now === null ? undefined : `Deadline ${at.toLocaleString(undefined, { weekday: "long", hour: "numeric", minute: "2-digit" })}`}
      className="flex h-9 items-stretch overflow-hidden rounded-md bg-[#0B0C0D] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08),0_2px_6px_rgba(0,0,0,0.25)]"
    >
      <span className="flex items-center bg-[#C8341F] px-2 font-display text-[14px] font-extrabold uppercase leading-none tracking-[0.04em] text-white">
        GW{gameweek ?? "—"}
      </span>
      <span
        className={`flex items-center gap-[3px] px-2 font-display text-[18px] font-extrabold leading-none tabular-nums sm:px-2.5 sm:text-[20px] ${
          urgent ? "animate-pulseDot" : ""
        }`}
        style={{ color: lit }}
      >
        {left === null ? (
          <span className="text-[#5BE38A]/40">--:--:--</span>
        ) : passed ? (
          <span className="text-[14px] uppercase tracking-[0.06em] text-white/70">Deadline passed</span>
        ) : (
          <>
            {d > 0 && <span>{d}D</span>}
            <span className={d > 0 ? "ml-1" : ""}>
              {pad(h)}:{pad(m)}:
            </span>
            <span key={s} className="inline-block min-w-[2ch] animate-tick">
              {pad(s)}
            </span>
          </>
        )}
      </span>
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
      className="grid h-9 w-9 flex-none place-items-center rounded-md border border-line text-ink-100 transition-colors hover:border-line-strong"
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
