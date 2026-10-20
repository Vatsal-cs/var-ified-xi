// File: VarMark.tsx
// Path: var-ified-xi/frontend/components/VarMark.tsx
//
// The site's mark, the same as the favicon: the referee's "check the screen"
// rectangle with a gold tick. It draws itself once when the page loads.

export default function VarMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden className="flex-none">
      <rect
        x="4.6"
        y="7.6"
        width="22.8"
        height="16.8"
        rx="2.6"
        fill="none"
        stroke="#F2EDE4"
        strokeWidth="2.3"
        pathLength={1}
        strokeDasharray="1"
        className="animate-draw"
      />
      <path
        d="M10.4 16.4 L14.4 20.1 L21.8 12.2"
        fill="none"
        stroke="#E0A64A"
        strokeWidth="3.1"
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1}
        strokeDasharray="1"
        className="animate-draw"
        style={{ animationDelay: "0.75s" }}
      />
    </svg>
  );
}
