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
