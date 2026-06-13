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

      {/* Region indicator — matches "Delhi, India" in mockup */}
      <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5">
        <MapPin size={14} className="text-blue-400" />
        <span className="text-sm text-gray-300">Delhi, India</span>
        <svg width="12" height="12" viewBox="0 0 12 12" className="text-gray-500">
          <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" />
        </svg>
      </div>

      {/* Time slider — center of top bar, matches mockup */}
      <div className="flex-1 flex flex-col items-center gap-1">
        <div className="flex items-center gap-3 w-full max-w-[500px]">
          <button onClick={() => setIsPlaying(v => !v)} className="text-gray-400 hover:text-white transition-colors flex-shrink-0">
            {isPlaying ? <Pause size={14} /> : <Play size={14} />}
          </button>
          <div className="flex-1 relative">
            {/* Slider track */}
            <div className="relative h-1 bg-white/10 rounded-full">
              <motion.div
                className="absolute h-full bg-blue-500 rounded-full"
                style={{ width: `${(timePosition / 6) * 100}%` }}
              />
              <input
                type="range" min={0} max={6} step={1} value={timePosition}
                onChange={e => setTime(Number(e.target.value))}
                className="absolute inset-0 w-full opacity-0 cursor-pointer h-4 -top-1.5"
              />
              {/* NOW marker */}
              <div className="absolute" style={{ left: `${(3/6)*100}%`, top: -2 }}>
                <div className="w-1 h-5 bg-blue-400/50 -translate-x-0.5" />
              </div>
              {/* Thumb */}
              <motion.div
                className="absolute w-3.5 h-3.5 bg-white rounded-full shadow-lg border border-blue-400 -top-[5px] -translate-x-1/2 cursor-grab"
                style={{ left: `${(timePosition / 6) * 100}%` }}
              />
            </div>
            {/* Time labels */}
            <div className="flex justify-between mt-1">
              {TIME_LABELS.map(label => (
                <span key={label} className={`text-[10px] ${label === "NOW" ? "text-blue-400 font-medium" : "text-gray-600"}`}>
                  {label}
                </span>
              ))}
            </div>
          </div>
        </div>
        {/* Current date/time display */}
        <span className="text-xs text-gray-500">May 18, 2025 &nbsp; 2:30 PM</span>
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-white border border-white/10 rounded-lg hover:bg-white/5 transition-all">
          <GitCompare size={14} /> Compare
        </button>
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-white border border-white/10 rounded-lg hover:bg-white/5 transition-all">
          <Download size={14} /> Export
        </button>
        <button className="relative p-2 text-gray-400 hover:text-white transition-colors">
          <Bell size={16} />
          {unacknowledgedCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 rounded-full text-white text-[10px] flex items-center justify-center font-bold">
              {unacknowledgedCount}
            </span>
          )}
        </button>
      </div>
    </div>
  );
}
```

---

## Step 4 — Build the Right Info Panel

Matches the right panel in the mockup: city name, weather, 4 metric cards (AQI/LST/NDVI/Risk Score), Risk Score gauge, Recent Alerts list, AQI Trend 7-day chart.

Create `src/components/panels/CityInfoPanel.tsx`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import { useDataStore } from "../../store/dataStore";
import EChartsReact from "echarts-for-react";
import { Star, Cloud } from "lucide-react";
import { cn } from "../../utils/cn";

export function CityInfoPanel() {
  const { activeRegion, activeZone } = useDataStore();

  const { data: scorecard } = useQuery({
    queryKey: ["scorecard", activeZone],
    queryFn:  () => api.getZoneScorecard(activeZone),
    enabled:  !!activeZone
  });

  const { data: forecast } = useQuery({
    queryKey: ["forecast", activeZone, "aq"],
    queryFn:  () => api.getForecast(activeZone, "aq"),
    enabled:  !!activeZone
  });

  const { data: insights } = useQuery({
    queryKey: ["insights", activeRegion],
    queryFn:  () => api.getInsights(activeRegion)
  });

  const s = scorecard?.data;

  const METRIC_CARDS = [
    { key: "aq",   label: "AQI",   value: s?.indicators?.aq?.current,   unit: "",    color: "#a855f7", bg: "bg-purple-500/10" },
    { key: "lst",  label: "LST",   value: s?.indicators?.lst?.current,  unit: "°C",  color: "#ef4444", bg: "bg-red-500/10"    },
    { key: "ndvi", label: "NDVI",  value: s?.indicators?.ndvi?.current, unit: "",    color: "#22c55e", bg: "bg-green-500/10"  },
    { key: "risk", label: "Risk",  value: s?.risk_score?.value,         unit: "/100",color: "#f97316", bg: "bg-orange-500/10" },
  ];

  // AQI trend chart config (matches the purple line chart in mockup)
  const aqi7DayOption = {
    backgroundColor: "transparent",
    grid: { top: 20, right: 10, bottom: 20, left: 30 },
    xAxis: {
      type: "category",
      data: ["May 12", "May 13", "May 14", "May 15", "May 16", "May 17", "May 18"],
      axisLine: { lineStyle: { color: "#ffffff10" } },
      axisLabel: { color: "#6b7280", fontSize: 10 }
    },
    yAxis: {
      type: "value",
      min: 0, max: 300,
      axisLine: { show: false },
      splitLine: { lineStyle: { color: "#ffffff08" } },
      axisLabel: { color: "#6b7280", fontSize: 10 }
    },
    series: [{
      type: "line",
      data: forecast?.data?.forecast?.slice(0,7).map((f:any) => Math.round(f.value)) ?? [],
      smooth: true,
      symbol: "none",
      lineStyle: { color: "#a855f7", width: 2 },
      areaStyle: {
        color: { type: "linear", x:0, y:0, x2:0, y2:1,
          colorStops: [
            { offset: 0, color: "rgba(168,85,247,0.3)" },
            { offset: 1, color: "rgba(168,85,247,0.0)" }
          ]
        }
      },
      markPoint: {
        data: [{ type: "max", symbolSize: 30,
          label: { color: "#fff", fontSize: 10 },
          itemStyle: { color: "#a855f7" }
        }]
      }
    }]
  };

  return (
    <div className="w-72 h-full bg-[#080c14]/90 border-l border-white/5 flex flex-col overflow-y-auto backdrop-blur-md flex-shrink-0">
      {/* City header — matches mockup top-right */}
      <div className="px-4 pt-4 pb-3 border-b border-white/5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-1.5">
              <h2 className="text-white font-bold text-lg leading-tight">Delhi</h2>
              <Star size={14} className="text-yellow-400" />
            </div>
            <div className="text-gray-500 text-xs">NCT, India</div>
          </div>
          <div className="flex items-center gap-1.5">
            <Cloud size={18} className="text-gray-400" />
            <span className="text-white font-bold">32°C</span>
            <span className="text-gray-500 text-xs">Haze</span>
          </div>
        </div>
      </div>

      {/* 4 metric cards — matches mockup */}
      <div className="grid grid-cols-2 gap-2 px-3 py-3">
        {METRIC_CARDS.map(card => (
          <div key={card.key} className={cn("rounded-xl p-3 border", card.bg, "border-white/5")}>
            <div className="text-xs text-gray-500 mb-1">{card.label}</div>
            <div className="text-xl font-bold" style={{ color: card.color }}>
              {card.value?.toFixed(card.key === "ndvi" ? 2 : 0) ?? "—"}{card.unit}
            </div>
            <div className="text-xs text-gray-600 mt-0.5">
              {s?.indicators?.[card.key]?.category ?? (card.key === "risk" ? s?.risk_score?.category : "")}
            </div>
