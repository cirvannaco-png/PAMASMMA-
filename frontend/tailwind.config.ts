import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        obsidian: {
          950: "#04040D",
          900: "#07071A",
          800: "#0C0C22",
          700: "#111130",
          600: "#1A1A3A",
          500: "#252550",
        },
        gold: {
          400: "#FFD700",
          500: "#D4AF37",
          600: "#B8960C",
        },
        silver: {
          300: "#F0F0F8",
          400: "#D0D0EC",
          500: "#A0A0C0",
          600: "#6060A0",
          700: "#3A3A6A",
        },
        magenta: {
          400: "#FF5B8B",
          500: "#E0387A",
          600: "#C0205A",
        },
        // System colors
        s1: "#6B3FFB",
        s2: "#00D4FF",
        s3: "#D4AF37",
        s4: "#3BFFA0",
        s5: "#FF5B8B",
        s6: "#FF8C42",
        s7: "#A97FFF",
        s8: "#FF4D6D",
        s9: "#5BFFD0",
        s10: "#FFD700",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Courier New", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        "2xl": "16px",
        "3xl": "24px",
      },
    },
  },
  plugins: [],
};

export default config;
