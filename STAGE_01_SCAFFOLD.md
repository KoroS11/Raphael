# Stage 01 — Project Scaffold

## Prerequisites
Stage 00 completed and verified.

## Objective
Create the full Raphael project structure using Tauri v2 as the shell and React + Vite as the frontend. By the end of this stage you will have a running desktop window that opens a blank React app.

---

## Step 1 — Create the Tauri Project

```
npm create tauri-app@latest raphael
```

When prompted:
```
Project name:          raphael
Frontend language:     TypeScript / JavaScript
Package manager:       npm
UI template:           React
UI flavor:             TypeScript
```

Enter the project:
```
cd raphael
```

---

## Step 2 — Install All Frontend Dependencies

Replace the contents of `package.json` with the full dependency list from `docs/TECHNICAL_SPECIFICATION.md` Section 1.1.

Then run:
```
npm install
```

This installs: deck.gl, Kepler.gl, MapLibre GL, Apache ECharts, shadcn/ui (via Radix UI), Framer Motion, Zustand, TanStack Query, react-i18next, Tauri plugins, PMTiles, and all dev dependencies.

---

## Step 3 — Install shadcn/ui

```
npx shadcn-ui@latest init
```

When prompted:
```
Style:                 Default
Base color:            Slate
CSS variables:         Yes
```

Then install the specific shadcn components Raphael uses:
```
npx shadcn-ui@latest add button card dialog dropdown-menu
npx shadcn-ui@latest add select slider switch tabs tooltip
npx shadcn-ui@latest add separator avatar badge progress
npx shadcn-ui@latest add sheet scroll-area
```

---

## Step 4 — Configure Tailwind

Replace `tailwind.config.ts` with:

```typescript
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background:   "hsl(var(--background))",
        foreground:   "hsl(var(--foreground))",
        sidebar:      "hsl(220 20% 8%)",
        "sidebar-fg": "hsl(220 10% 70%)",
        panel:        "hsl(220 15% 11%)",
        "panel-fg":   "hsl(220 10% 80%)",
        border:       "hsl(var(--border))",
        ring:         "hsl(var(--ring))",
        primary:      { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        muted:        { DEFAULT: "hsl(var(--muted))",   foreground: "hsl(var(--muted-foreground))"  },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
```

Install the animate plugin:
```
npm install tailwindcss-animate
```

---

## Step 5 — Create the Full Folder Structure

Create every folder in the structure below. Create a `.gitkeep` file inside each empty folder so git tracks them.

```
src/
  components/
    ui/              (shadcn components live here automatically)
    map/
    charts/
    panels/
    layout/
  views/
    ExplorerView/
    DashboardView/
    RiskIntelligenceView/
    AnalyticsView/
