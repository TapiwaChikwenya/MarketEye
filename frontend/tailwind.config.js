/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        sans: [
          '"DM Sans"',
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        display: [
          '"Fraunces"',
          '"DM Sans"',
          "Georgia",
          "serif",
        ],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        brass: {
          DEFAULT: "hsl(var(--brass))",
          foreground: "hsl(var(--brass-foreground))",
        },
        ink: {
          DEFAULT: "hsl(var(--ink))",
          elevated: "hsl(var(--ink-elevated))",
        },
        neon: {
          cyan: "hsl(var(--primary))",
          magenta: "hsl(var(--destructive))",
          lime: "hsl(var(--success))",
          pink: "#e11d48",
          blue: "hsl(var(--primary))",
          purple: "#6366f1",
        },
        cyber: {
          dark: "hsl(var(--background))",
          darker: "hsl(var(--muted))",
          purple: "#6366f1",
          pink: "#e11d48",
          cyan: "hsl(var(--primary))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
        glow: {
          "0%, 100%": { boxShadow: "0 2px 12px hsl(var(--primary) / 0.2)" },
          "50%": { boxShadow: "0 6px 24px hsl(var(--primary) / 0.28)" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.5 },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        glow: "glow 2s ease-in-out infinite",
        "pulse-glow": "pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "cyber-grid":
          "linear-gradient(rgba(15, 23, 42, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(15, 23, 42, 0.05) 1px, transparent 1px)",
        "mesh-hero":
          "radial-gradient(ellipse 80% 60% at 20% 10%, hsl(217 91% 44% / 0.12), transparent 55%), radial-gradient(ellipse 70% 50% at 85% 30%, hsl(43 62% 52% / 0.08), transparent 50%), radial-gradient(ellipse 60% 45% at 50% 95%, hsl(152 69% 36% / 0.06), transparent 45%)",
        "section-soft":
          "linear-gradient(180deg, hsl(40 33% 97%) 0%, hsl(40 28% 98%) 45%, hsl(40 25% 99%) 100%)",
        "hero-dark":
          "radial-gradient(ellipse 90% 70% at 15% 20%, hsl(217 91% 44% / 0.15), transparent 55%), radial-gradient(ellipse 60% 50% at 90% 10%, hsl(43 62% 52% / 0.08), transparent 45%)",
      },
      boxShadow: {
        lift: "0 2px 8px -2px rgba(15, 23, 42, 0.06), 0 12px 28px -8px rgba(15, 23, 42, 0.1)",
        "lift-lg": "0 4px 16px -4px rgba(15, 23, 42, 0.08), 0 24px 48px -12px rgba(15, 23, 42, 0.14)",
        glow: "0 0 0 1px hsl(var(--primary) / 0.12), 0 12px 40px -8px hsl(var(--primary) / 0.22)",
        "inset-brass": "inset 0 1px 0 rgba(255,255,255,0.12)",
      },
      backgroundSize: {
        grid: "48px 48px",
      },
    },
  },
  plugins: [],
}
