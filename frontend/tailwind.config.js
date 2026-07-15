/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        pitch: {
          night: "#0B0F0D",
          panel: "#151B19",
          panel2: "#1C2420",
          line: "#26332C",
        },
        var: {
          green: "#00FF87",
          greendim: "#0A8F52",
          crimson: "#FF3864",
          amber: "#FFB800",
        },
        ink: {
          100: "#EDEFEA",
          300: "#B7C2BC",
          500: "#7C8A83",
        },
      },
      fontFamily: {
        display: ["var(--font-oswald)", "sans-serif"],
        mono: ["var(--font-jbmono)", "monospace"],
        body: ["var(--font-inter)", "sans-serif"],
      },
      keyframes: {
        scanline: {
          "0%": { transform: "translateY(-10%)", opacity: "0" },
          "10%": { opacity: "1" },
          "90%": { opacity: "1" },
          "100%": { transform: "translateY(110%)", opacity: "0" },
        },
        stamp: {
          "0%": { transform: "scale(2.2) rotate(-8deg)", opacity: "0" },
          "60%": { transform: "scale(0.92) rotate(-8deg)", opacity: "1" },
          "100%": { transform: "scale(1) rotate(-8deg)", opacity: "1" },
        },
        pulseDot: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
        fadeUp: {
          "0%": { transform: "translateY(8px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
      },
      animation: {
        scanline: "scanline 2.4s ease-in-out 1",
        stamp: "stamp 0.5s cubic-bezier(0.2,0.8,0.2,1) forwards",
        pulseDot: "pulseDot 1.6s ease-in-out infinite",
        fadeUp: "fadeUp 0.5s ease-out forwards",
      },
    },
  },
  plugins: [],
};