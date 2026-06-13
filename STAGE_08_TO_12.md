# Stage 08 — Full Dashboard UI

## Prerequisites
Stage 07 completed. Map canvas rendering with live data.

## Objective
Build the complete dashboard layout matching the mockup exactly. This includes the sidebar navigation, top bar with time slider, right panel with city metrics, the six bottom data panels, and the full shell. Every element visible in the mockup must be implemented.

---

## Step 1 — Build the Shell Layout

Create `src/components/layout/Shell.tsx`:

```typescript
import { ReactNode, useState } from "react";
import { Sidebar }  from "./Sidebar";
import { TopBar }   from "./TopBar";
import { motion }   from "framer-motion";

export function Shell({ children }: { children: ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen w-screen bg-[#0d1117] text-white overflow-hidden select-none">
      {/* Left Sidebar — 140px wide, matches mockup exactly */}
      <motion.div
        animate={{ width: sidebarCollapsed ? 56 : 140 }}
        transition={{ type: "spring", damping: 25 }}
        className="flex-shrink-0 h-full bg-[#080c14] border-r border-white/5 flex flex-col z-20"
      >
        <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(v => !v)} />
      </motion.div>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar — time slider + search + actions */}
        <TopBar />

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {children}
        </div>
      </div>
    </div>
  );
}
```

---

## Step 2 — Build the Sidebar

Matches the mockup exactly: Raphael logo at top, nav items with icons, user profile and system status at bottom.

Create `src/components/layout/Sidebar.tsx`:

```typescript
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Map, Radio, ShieldAlert,
  BarChart2, Bell, FileText, Database,
  Settings, ChevronRight
} from "lucide-react";
import { useSystemStore } from "../../store/systemStore";

const NAV_ITEMS = [
  { path: "/explorer",    icon: Map,           label: "Explorer"     },
  { path: "/",            icon: LayoutDashboard,label: "Dashboard"    },
  { path: "/map",         icon: Map,           label: "Map Explorer" },
  { path: "/monitor",     icon: Radio,         label: "Live Monitor" },
  { path: "/risk",        icon: ShieldAlert,   label: "Risk Intel"   },
  { path: "/analytics",   icon: BarChart2,     label: "Analytics"    },
  { path: "/alerts",      icon: Bell,          label: "Alerts"       },
  { path: "/reports",     icon: FileText,      label: "Reports"      },
  { path: "/catalog",     icon: Database,      label: "Data Catalog" },
  { path: "/settings",    icon: Settings,      label: "Settings"     },
];

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const location     = useLocation();
  const { services } = useSystemStore();
  const allHealthy   = Object.values(services).every(s => s);

  return (
    <div className="flex flex-col h-full py-3">
      {/* Logo */}
      <div className="px-3 mb-6">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center flex-shrink-0">
            <span className="text-white font-bold text-sm">R</span>
          </div>
          {!collapsed && (
            <div>
              <div className="text-white font-bold text-sm leading-tight">RAPHAEL</div>
              <div className="text-gray-500 text-xs leading-tight">Environmental Intelligence</div>
            </div>
          )}
        </div>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-2 space-y-0.5">
        {NAV_ITEMS.map(item => {
          const isActive = location.pathname === item.path;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`
                flex items-center gap-3 px-2.5 py-2 rounded-lg text-xs transition-all
                ${isActive
                  ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                  : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
                }
              `}
            >
              <item.icon size={16} className="flex-shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
              {!collapsed && isActive && (
                <ChevronRight size={12} className="ml-auto text-blue-400" />
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* User profile — bottom of sidebar, matches mockup */}
      <div className="px-3 mt-4 pt-4 border-t border-white/5">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center flex-shrink-0">
            <span className="text-white text-xs font-bold">A</span>
          </div>
          {!collapsed && (
            <div>
              <div className="text-white text-xs font-medium">Avinash</div>
              <div className="text-gray-500 text-xs">Admin</div>
            </div>
          )}
        </div>
        {/* System status indicator — matches mockup "All Systems Operational" */}
        {!collapsed && (
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${allHealthy ? "bg-green-400" : "bg-yellow-400"} animate-pulse`} />
            <span className="text-xs text-gray-500">{allHealthy ? "Operational" : "Degraded"}</span>
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## Step 3 — Build the Top Bar with Time Slider

Matches mockup exactly: left search box, center time slider (-7D to +30D with NOW marker), right compare/export/notifications.

Create `src/components/layout/TopBar.tsx`:

```typescript
import { Search, MapPin, Play, Pause, Bell, GitCompare, Download } from "lucide-react";
import { useState, useRef } from "react";
import { useMapStore } from "../../store/mapStore";
import { useAlertStore } from "../../store/alertStore";
import { motion } from "framer-motion";

const TIME_LABELS = ["-7D", "-3D", "-24H", "NOW", "+24H", "+7D", "+30D"];

export function TopBar() {
  const { timePosition, setTime } = useMapStore();
  const { unacknowledgedCount }   = useAlertStore();
  const [isPlaying, setIsPlaying] = useState(false);
  const [searchVal, setSearchVal] = useState("");

  return (
    <div className="flex items-center h-14 px-4 gap-4 border-b border-white/5 bg-[#080c14]/80 backdrop-blur-sm flex-shrink-0">
      {/* Location search */}
      <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 min-w-[240px]">
        <Search size={14} className="text-gray-500" />
        <input
          value={searchVal}
          onChange={e => setSearchVal(e.target.value)}
          placeholder="Search location..."
          className="bg-transparent text-sm text-gray-300 placeholder-gray-600 outline-none flex-1"
        />
        <kbd className="text-xs text-gray-600 bg-white/5 px-1 rounded">Ctrl K</kbd>
      </div>
