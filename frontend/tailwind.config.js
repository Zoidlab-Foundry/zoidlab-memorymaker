/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0f1119", panel: "#181b27", panel2: "#1e2130", line: "#2a2d3a",
        cy: "#4fd1c5", vi: "#7c5cfc", ind: "#818cf8", prism: "#c026d3",
        ink: "#e8e9ef", dim: "#9aa0b0", faint: "#6b7180",
        ok: "#22c55e", warn: "#f4b860", bad: "#ef4444",
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(124,92,250,0.45)",
      },
    },
  },
  plugins: [],
};
