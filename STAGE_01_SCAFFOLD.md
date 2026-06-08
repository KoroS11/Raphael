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
    ComparisonView/
    AlertsView/
    ReportsView/
    DataCatalogView/
    SettingsView/
  store/
  api/
  i18n/
    locales/
  types/
  utils/

backend/
  api/
    routes/
    models/
  db/
    migrations/
      versions/
  ingestion/
    flows/
  processing/
  ml/
  reports/
    templates/

mage/
  pipelines/
    csv_import/
    geojson_import/
    kml_import/
    shapefile_import/
    excel_import/
  custom/

config/
data/
  tiles/
  boundaries/
scripts/
tests/
  ingestion/
  ml/
  api/
```

---

## Step 6 — Set Up Python Virtual Environment

```
python -m venv backend/.venv
```

Activate:
```
# Windows
backend\.venv\Scripts\activate

# Linux / macOS
source backend/.venv/bin/activate
```

Install all backend dependencies from `docs/TECHNICAL_SPECIFICATION.md` Section 1.2:
```
pip install -r backend/requirements.txt
```

This installs: FastAPI, Prefect, Mage.ai, scikit-learn, Prophet, MLflow, Rasterio, GeoPandas, WeasyPrint, Playwright, and all other dependencies.

---

## Step 7 — Configure Tauri

Replace `src-tauri/tauri.conf.json` with:

```json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "Raphael",
  "version": "1.0.0",
  "identifier": "com.raphael.environmental",
  "build": {
    "frontendDist": "../dist",
    "devUrl": "http://localhost:5173",
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build"
  },
  "app": {
    "windows": [
      {
        "title": "Raphael — Environmental Intelligence",
        "width": 1440,
        "height": 900,
        "minWidth": 1280,
        "minHeight": 720,
        "resizable": true,
        "fullscreen": false,
        "decorations": false
      }
    ],
    "trayIcon": {
      "iconPath": "icons/tray-icon.png",
      "iconAsTemplate": true
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ]
  },
  "plugins": {
    "shell": {
      "open": true,
      "sidecar": true
    },
    "notification": { "all": true },
    "fs": { "all": true, "scope": ["$APPDATA/raphael/**"] },
    "dialog": { "all": true }
  }
}
```

---

## Step 8 — Update Cargo.toml

Replace `src-tauri/Cargo.toml` with the full version from `docs/TECHNICAL_SPECIFICATION.md` Section 1.3.

Then run:
```
cd src-tauri
cargo fetch
cd ..
```

---

## Step 9 — Create App Shell Layout

Create `src/App.tsx`:

```typescript
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Shell } from "./components/layout/Shell";
import { ExplorerView } from "./views/ExplorerView";
import { DashboardView } from "./views/DashboardView";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 1000 * 60 * 5, retry: 1 },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Shell>
          <Routes>
            <Route path="/"          element={<DashboardView />} />
            <Route path="/explorer"  element={<ExplorerView />} />
          </Routes>
        </Shell>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

Install react-router-dom:
```
npm install react-router-dom
```

---

## Step 10 — Create Global CSS Variables

Replace contents of `src/index.css` with:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 220 20% 7%;
    --foreground: 220 10% 90%;
    --muted: 220 15% 14%;
    --muted-foreground: 220 10% 55%;
    --border: 220 15% 18%;
    --primary: 199 89% 48%;
    --primary-foreground: 220 20% 7%;
    --ring: 199 89% 48%;
    --radius: 0.5rem;
  }
}

* { border-color: hsl(var(--border)); }
body {
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  font-family: "Inter", system-ui, sans-serif;
  overflow: hidden;
}

/* Hide scrollbar but keep scroll functionality */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: hsl(var(--border)); border-radius: 2px; }
```

---

## Step 11 — Create Configuration Files

Create `config/app.toml` using the full content from `docs/TECHNICAL_SPECIFICATION.md` Section 2.1.

Create `config/datasources.toml` using the full content from `docs/TECHNICAL_SPECIFICATION.md` Section 2.2.

Create `config/ml.toml` using the full content from `docs/TECHNICAL_SPECIFICATION.md` Section 2.3.

Copy `.env` from Stage 00 into the project root.

---

## Step 12 — Verify the Scaffold Runs

```
npm run tauri dev
```

Expected result: A dark desktop window opens showing a blank React app with no errors in the terminal.

If the window opens successfully, Stage 01 is complete.

---

## Verification Checklist

```
Tauri window opens with no errors
npm run build completes without TypeScript errors
cargo check passes in src-tauri/
backend/.venv exists with all packages installed
All folders in the structure above exist
config/app.toml, datasources.toml, ml.toml exist
.env exists in project root
```
