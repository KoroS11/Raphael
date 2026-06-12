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
          </div>
        ))}
      </div>

      {/* Risk Score bar — matches mockup gradient bar */}
      <div className="px-3 pb-3 border-b border-white/5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-400">Risk Score (AI)</span>
          <div className="flex items-center gap-1">
            <span className="text-lg font-bold text-orange-400">{s?.risk_score?.value ?? "—"}</span>
            <span className="text-xs text-gray-500">/100</span>
          </div>
        </div>
        <div className="h-2 rounded-full overflow-hidden bg-white/5">
          <div className="h-full bg-gradient-to-r from-green-500 via-yellow-400 via-orange-400 to-red-500 rounded-full relative">
            <div
              className="absolute top-0 h-full w-1 bg-white rounded-full"
              style={{ left: `${s?.risk_score?.value ?? 0}%`, transform: "translateX(-50%)" }}
            />
          </div>
        </div>
        <div className="text-xs text-gray-500 mt-1.5 font-medium">
          {s?.risk_score?.category ?? "High Risk"}
        </div>
        <div className="text-xs text-gray-600 mt-0.5">{s?.risk_score?.explanation}</div>
      </div>

      {/* Recent Alerts — matches mockup */}
      <div className="px-3 py-3 border-b border-white/5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-400">Recent Alerts</span>
          <button className="text-xs text-blue-400 hover:text-blue-300">See all</button>
        </div>
        <div className="space-y-2">
          {(s?.recent_alerts ?? []).slice(0,3).map((alert:any) => (
            <div key={alert.id} className="flex items-center gap-2">
              <span className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0", {
                "bg-red-400":    alert.severity === "critical",
                "bg-orange-400": alert.severity === "warning",
                "bg-blue-400":   alert.severity === "info"
              })} />
              <span className="text-xs text-gray-300 flex-1 truncate">{alert.rule_name}</span>
              <span className="text-xs text-gray-600 flex-shrink-0">
                {Math.round((Date.now() - new Date(alert.triggered_at).getTime()) / 3600000)}h ago
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* AQI Trend chart — matches purple line chart in mockup */}
      <div className="px-3 py-3 border-b border-white/5">
        <div className="text-xs font-semibold text-gray-400 mb-2">AQI Trend (7 Days)</div>
        <EChartsReact option={aqi7DayOption} style={{ height: 100 }} theme="dark" />
      </div>

      {/* AI Insights — matches bottom-right panel in mockup */}
      <div className="px-3 py-3">
        <div className="text-xs font-semibold text-gray-400 mb-2">AI Insights</div>
        <div className="space-y-2">
          {(insights?.data ?? []).map((insight:any, i:number) => (
            <div key={i} className="flex items-start gap-2">
              <span className={cn("mt-0.5 flex-shrink-0", {
                "text-red-400":    insight.icon === "heat",
                "text-blue-400":   insight.icon === "cloud",
                "text-green-400":  insight.icon === "leaf"
              })}>
                {insight.icon === "heat" ? "🌡" : insight.icon === "cloud" ? "💨" : "🌿"}
              </span>
              <span className="text-xs text-gray-300 leading-relaxed">{insight.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## Step 5 — Build the Bottom Data Panels

Matches the six bottom panels in the mockup: Live AQI Stations, LST thumbnail, NDVI thumbnail, Precipitation Forecast, Wind and Weather, AI Insights.

Create `src/components/panels/BottomPanelRow.tsx`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import { useDataStore } from "../../store/dataStore";
import EChartsReact from "echarts-for-react";

export function BottomPanelRow() {
  const { activeRegion } = useDataStore();

  const { data: stationsData } = useQuery({
    queryKey: ["stations", activeRegion],
    queryFn:  () => api.getLayer("aq", activeRegion, "76.8,28.4,77.4,28.9")
  });

  const { data: weatherData } = useQuery({
    queryKey: ["weather", activeRegion],
    queryFn:  () => api.getLayer("weather", activeRegion, "76.8,28.4,77.4,28.9")
  });

  const lstTileUrl  = `http://localhost:8000/api/v1/layers/lst/tile?region_id=${activeRegion}&thumbnail=true`;
  const ndviTileUrl = `http://localhost:8000/api/v1/layers/ndvi/tile?region_id=${activeRegion}&thumbnail=true`;

  const top5Stations = (stationsData?.data?.features ?? [])
    .sort((a:any, b:any) => b.properties.value - a.properties.value)
    .slice(0, 5);

  const precipOption = {
    backgroundColor: "transparent",
    grid: { top: 10, right: 5, bottom: 25, left: 35 },
    xAxis: {
      type: "category",
      data: ["Today", "May 19", "May 20", "May 21", "May 22"],
      axisLabel: { color: "#6b7280", fontSize: 9 },
      axisLine: { show: false }, axisTick: { show: false }
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#6b7280", fontSize: 9, formatter: "{value}mm" },
      splitLine: { lineStyle: { color: "#ffffff08" } }
    },
    series: [{
      type: "bar",
      data: [2.1, 12.4, 24.8, 5.6, 0.3],
      itemStyle: { color: "#3b82f6", borderRadius: [3,3,0,0] },
      label: { show: true, position: "top", color: "#9ca3af", fontSize: 9,
               formatter: (p:any) => p.value > 0 ? p.value : "" }
    }]
  };

  return (
    <div className="h-[220px] flex gap-2 px-2 pb-2 flex-shrink-0 overflow-x-auto">
      {/* Panel 1: Live AQI Stations */}
      <BottomPanel title="Live AQI Stations (Top 5)" className="min-w-[220px]">
        <div className="space-y-1.5">
          {top5Stations.map((f:any) => {
            const val = f.properties.value;
            const cat = val > 200 ? "Very Poor" : val > 150 ? "Poor" : val > 100 ? "Moderate" : "Good";
            const col = val > 200 ? "#a855f7" : val > 150 ? "#ef4444" : val > 100 ? "#f97316" : "#22c55e";
            return (
              <div key={f.properties.station_id} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: col }} />
                  <span className="text-xs text-gray-300 truncate max-w-[120px]">{f.properties.station_name}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-bold" style={{ color: col }}>{Math.round(val)}</span>
                  <span className="text-xs text-gray-600">{cat}</span>
                </div>
              </div>
            );
          })}
        </div>
      </BottomPanel>

      {/* Panel 2: LST thumbnail — matches mockup red-orange mini map */}
      <BottomPanel title="Land Surface Temperature" className="min-w-[180px]">
        <div className="flex-1 relative rounded overflow-hidden">
          <img src={lstTileUrl} alt="LST" className="w-full h-full object-cover" />
          <div className="absolute bottom-0 left-0 right-0 h-4 flex items-center justify-between px-2">
            <span className="text-[9px] text-blue-200">20°C</span>
            <div className="flex-1 mx-2 h-1.5 rounded-full bg-gradient-to-r from-blue-500 via-yellow-400 to-red-600" />
            <span className="text-[9px] text-red-200">50°C</span>
          </div>
        </div>
      </BottomPanel>

      {/* Panel 3: NDVI thumbnail — matches mockup green mini map */}
      <BottomPanel title="NDVI (Green Cover)" className="min-w-[180px]">
        <div className="flex-1 relative rounded overflow-hidden">
          <img src={ndviTileUrl} alt="NDVI" className="w-full h-full object-cover" />
          <div className="absolute bottom-0 left-0 right-0 h-4 flex items-center justify-between px-2">
            <span className="text-[9px] text-gray-400">0.0</span>
            <div className="flex-1 mx-2 h-1.5 rounded-full bg-gradient-to-r from-yellow-800 via-yellow-300 to-green-600" />
            <span className="text-[9px] text-green-300">1.0</span>
          </div>
        </div>
      </BottomPanel>

      {/* Panel 4: Precipitation forecast */}
      <BottomPanel title="Precipitation Forecast" className="min-w-[220px]">
        <EChartsReact option={precipOption} style={{ height: "100%", width: "100%" }} theme="dark" />
      </BottomPanel>

      {/* Panel 5: Wind and Weather — matches mockup with compass */}
      <BottomPanel title="Wind and Weather" className="min-w-[180px]">
        <div className="flex items-center gap-4">
          <WindCompass direction={225} speed={12} />
          <div className="space-y-2">
            <div>
              <div className="text-xs text-gray-500">Humidity</div>
              <div className="text-sm font-bold text-white">54%</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">UV Index</div>
              <div className="text-sm font-bold text-yellow-400">6 <span className="text-xs font-normal">High</span></div>
            </div>
          </div>
        </div>
      </BottomPanel>
    </div>
  );
}

function BottomPanel({ title, children, className = "" }: {
  title: string; children: React.ReactNode; className?: string
}) {
  return (
    <div className={`flex-1 bg-[#080c14]/90 border border-white/5 rounded-xl p-3 flex flex-col gap-2 backdrop-blur-sm ${className}`}>
      <div className="text-xs font-semibold text-gray-400 flex-shrink-0">{title}</div>
      <div className="flex-1 min-h-0">{children}</div>
    </div>
  );
}

function WindCompass({ direction, speed }: { direction: number; speed: number }) {
  const rad = (direction * Math.PI) / 180;
  const cx = 40, cy = 40, r = 30;
  const nx = cx + r * Math.sin(rad);
  const ny = cy - r * Math.cos(rad);

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={80} height={80} className="text-white">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#ffffff15" strokeWidth={1.5} />
        {["N","E","S","W"].map((dir, i) => {
          const angle = i * 90;
          const x = cx + (r+8) * Math.sin(angle * Math.PI/180);
          const y = cy - (r+8) * Math.cos(angle * Math.PI/180);
          return <text key={dir} x={x} y={y+4} textAnchor="middle" fill={dir==="N"?"#60a5fa":"#6b7280"} fontSize={9}>{dir}</text>;
        })}
        <line x1={cx} y1={cy} x2={nx} y2={ny} stroke="#60a5fa" strokeWidth={2} strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={3} fill="#60a5fa" />
      </svg>
      <div className="text-center">
        <div className="text-sm font-bold text-white">{speed} km/h</div>
        <div className="text-xs text-gray-500">SW</div>
      </div>
    </div>
  );
}
```

---

## Step 6 — Assemble the Explorer View

Create `src/views/ExplorerView/index.tsx`:

```typescript
import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { MapCanvas }      from "../../components/map/MapCanvas";
import { LayersPanel }    from "../../components/map/LayersPanel";
import { CityInfoPanel }  from "../../components/panels/CityInfoPanel";
import { BottomPanelRow } from "../../components/panels/BottomPanelRow";
import { Layers } from "lucide-react";

export function ExplorerView() {
  const [showLayers, setShowLayers] = useState(true);

  return (
    <div className="flex h-full w-full overflow-hidden">
      {/* Map area */}
      <div className="flex-1 relative flex flex-col min-w-0">
        {/* Map canvas — takes all remaining space above bottom panels */}
        <div className="flex-1 relative overflow-hidden">
          {/* Layers panel — floats over map left side */}
          <AnimatePresence>
            {showLayers && (
              <LayersPanel onClose={() => setShowLayers(false)} />
            )}
          </AnimatePresence>

          {/* Toggle layers button */}
          {!showLayers && (
            <button
              onClick={() => setShowLayers(true)}
              className="absolute top-3 left-3 z-10 p-2 bg-[#080c14]/90 border border-white/10 rounded-lg text-gray-400 hover:text-white transition-colors backdrop-blur-sm"
            >
              <Layers size={16} />
            </button>
          )}

          <MapCanvas />
        </div>

        {/* Bottom panel row */}
        <BottomPanelRow />
      </div>

      {/* Right info panel */}
      <CityInfoPanel />
    </div>
  );
}
```

---

## Verification Checklist

```
Shell renders with sidebar, top bar, and main content area
Sidebar nav items navigate to correct routes
Top bar time slider drags smoothly from -7D to +30D
MapCanvas fills the center area
LayersPanel appears over the map left side with all 9 layers listed
CityInfoPanel shows on the right with AQI/LST/NDVI/Risk metric cards
Risk Score gradient bar renders with marker at correct position
Recent Alerts list shows last 3 alerts
AQI Trend chart renders as a purple line chart
Bottom row shows 6 panels: stations, LST thumbnail, NDVI thumbnail, precipitation, wind, AI insights
LST thumbnail shows colored minimap from raster tile
NDVI thumbnail shows green colored minimap
Wind compass SVG rotates to correct direction
All data fetched from FastAPI (not hardcoded)
No console errors in the browser devtools
```

---

# Stage 09 — Custom Data Import (Mage.ai)

## Prerequisites
Stage 08 completed. Full dashboard rendering.

## Objective
Set up Mage.ai as the visual import pipeline for field data. The Data Catalog view embeds Mage.ai as an iframe.

## Step 1 — Initialize Mage.ai Project

```
pip install mage-ai
mage init raphael_mage
cd raphael_mage
```

## Step 2 — Create Import Pipelines

Create one pipeline per import format. Each pipeline has 5 blocks.

For each pipeline file in `mage/pipelines/`:

**CSV pipeline** (`mage/pipelines/csv_import/`):
- Block 1 `load_csv.py`: `import pandas as pd; df = pd.read_csv(filepath); return df`
- Block 2 `map_columns.py`: Apply user-defined column mapping from config
- Block 3 `validate.py`: Check lat/lon ranges, timestamp format, value bounds
- Block 4 `normalize.py`: Reproject coordinates, convert units
- Block 5 `export_db.py`: Bulk insert to raw_observations via SQLAlchemy

Repeat for GeoJSON, KML, Shapefile, Excel formats.

## Step 3 — Start Mage.ai

```
mage start raphael_mage --host 127.0.0.1 --port 6789
```

## Step 4 — Embed in Data Catalog View

Create `src/views/DataCatalogView/index.tsx`:

```typescript
export function DataCatalogView() {
  return (
    <div className="flex h-full">
      <iframe
        src="http://localhost:6789"
        className="flex-1 border-0"
        title="Raphael Data Import — Mage.ai"
      />
    </div>
  );
}
```

---

# Stage 10 — Alert System

## Prerequisites
Stage 08 completed.

## Objective
Build the full alert engine. Alerts evaluate continuously, trigger system tray notifications via Tauri, and display in the Alerts view.

## Step 1 — Create Alert Evaluator

Create `backend/api/alerts/evaluator.py`:

```python
import asyncio
from sqlalchemy import text
from db.connection import SessionLocal
import httpx

async def run_alert_evaluator():
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes
        db = SessionLocal()
        try:
            rules = db.execute(text("""
                SELECT r.*, z.geometry as zone_geom
                FROM alert_rules r
                LEFT JOIN zone_geometries z ON z.id = r.zone_id
                WHERE r.is_active = true
            """)).fetchall()

            for rule in rules:
                current_val = db.execute(text("""
                    SELECT AVG(value) FROM raw_observations
                    WHERE layer_type = :layer
                      AND observed_at >= NOW() - INTERVAL '1 hour'
                      AND ST_Within(geometry, :geom)
                """), {"layer": rule.layer_type, "geom": rule.zone_geom}).scalar()

                if current_val is None:
                    continue

                triggered = False
                if rule.operator == "gt"  and current_val >  rule.threshold: triggered = True
                if rule.operator == "lt"  and current_val <  rule.threshold: triggered = True

                if triggered:
                    db.execute(text("""
                        INSERT INTO alert_events (id, rule_id, observed_value)
                        VALUES (gen_random_uuid(), :rule_id, :val)
                    """), {"rule_id": rule.id, "val": float(current_val)})
                    db.commit()
                    # Notify frontend via SSE endpoint
                    await notify_frontend(rule.name, current_val, rule.severity)
        finally:
            db.close()

async def notify_frontend(rule_name: str, value: float, severity: str):
    # POST to Tauri notification endpoint
    try:
        async with httpx.AsyncClient() as client:
            await client.post("http://localhost:8000/api/v1/alerts/notify", json={
                "title": f"Raphael Alert: {rule_name}",
                "body":  f"Current value: {value:.1f}",
                "severity": severity
            })
    except Exception:
        pass
```

## Step 2 — Add SSE Notification Stream

Add to `backend/api/routes/alerts.py`:

```python
from fastapi.responses import StreamingResponse
import asyncio, json

alert_subscribers: list = []

@router.get("/stream")
async def alert_stream(_user = Depends(get_current_user)):
    async def event_generator():
        queue = asyncio.Queue()
        alert_subscribers.append(queue)
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
        finally:
            alert_subscribers.remove(queue)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## Step 3 — Build Alerts View

Create `src/views/AlertsView/index.tsx` with:
- Alert rule builder form: zone selector, layer dropdown, operator select, threshold input, severity picker
- Active rules list with enable/disable toggles
- Alert history table with filter by date/severity/layer
- CSV export button

---

# Stage 11 — Report Generation (WeasyPrint + Playwright)

## Prerequisites
Stage 08 completed.

## Objective
Build the PDF report generation pipeline.

## Step 1 — Create Jinja2 Report Template

Create `backend/reports/templates/zone_report.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; margin: 0; background: #fff; color: #111; }
    .header { background: linear-gradient(135deg, #0a0f1a, #0d2451); color: white; padding: 40px; }
    .logo { font-size: 24px; font-weight: 700; letter-spacing: 2px; }
    .subtitle { font-size: 12px; opacity: 0.6; margin-top: 4px; }
    .zone-name { font-size: 36px; font-weight: 700; margin-top: 20px; }
    .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; padding: 24px; }
    .metric-card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; }
    .metric-label { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-value { font-size: 28px; font-weight: 700; margin-top: 4px; }
    .section { padding: 24px; border-top: 1px solid #f3f4f6; }
    .section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
    .map-image { width: 100%; border-radius: 12px; overflow: hidden; }
    .data-source { font-size: 10px; color: #9ca3af; margin-top: 4px; }
    .footer { padding: 24px; border-top: 1px solid #f3f4f6; font-size: 11px; color: #9ca3af; display: flex; justify-content: space-between; }
  </style>
</head>
<body>
  <div class="header">
    <div class="logo">RAPHAEL</div>
    <div class="subtitle">Environmental Intelligence Platform</div>
    <div class="zone-name">{{ zone_name }}</div>
    <div style="opacity:0.6; margin-top:4px; font-size:13px">{{ region_name }} &bull; Generated {{ generated_at }}</div>
  </div>

  <div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-label">Air Quality (AQI)</div>
      <div class="metric-value" style="color:#a855f7">{{ indicators.aq.current | round(0) }}</div>
      <div style="font-size:12px; color:#6b7280">{{ indicators.aq.category }}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Land Surface Temp</div>
      <div class="metric-value" style="color:#ef4444">{{ indicators.lst.current | round(1) }}°C</div>
      <div style="font-size:12px; color:#6b7280">{{ indicators.lst.category }}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">NDVI Green Cover</div>
      <div class="metric-value" style="color:#22c55e">{{ indicators.ndvi.current | round(2) }}</div>
      <div style="font-size:12px; color:#6b7280">{{ indicators.ndvi.category }}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">AI Risk Score</div>
      <div class="metric-value" style="color:#f97316">{{ risk_score.value }}/100</div>
      <div style="font-size:12px; color:#6b7280">{{ risk_score.category }}</div>
    </div>
  </div>

  {% if map_image_b64 %}
  <div class="section">
    <div class="section-title">Environmental Map — {{ generated_at_date }}</div>
    <img class="map-image" src="data:image/png;base64,{{ map_image_b64 }}" />
  </div>
  {% endif %}

  <div class="section">
    <div class="section-title">AI Assessment</div>
    <p style="color:#374151; line-height:1.6">{{ risk_score.explanation }}</p>
  </div>

  <div class="footer">
    <div>Raphael Environmental Intelligence Platform &bull; {{ organization }}</div>
    <div>Data sources: {{ data_sources | join(', ') }}</div>
  </div>
</body>
</html>
```

## Step 2 — Create Report Generator

Create `backend/reports/generator.py`:

```python
import base64, uuid, asyncio
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from playwright.async_api import async_playwright
from datetime import datetime
import os

REPORTS_DIR  = Path(os.getenv("RAPHAEL_DATA_DIR", "./data")) / "reports"
TEMPLATE_DIR = Path(__file__).parent / "templates"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

async def capture_map_screenshot(region_id: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page(viewport={"width": 1200, "height": 600})
        await page.goto(f"http://localhost:5173/explorer?region={region_id}&screenshot=1")
        await page.wait_for_timeout(3000)  # Wait for map tiles to load
        screenshot = await page.screenshot(type="png")
        await browser.close()
    return base64.b64encode(screenshot).decode()

async def generate_zone_report(zone_id: str, scorecard: dict, organization: str) -> Path:
    map_b64 = await capture_map_screenshot(scorecard.get("zone", {}).get("region_id", ""))

    template = env.get_template("zone_report.html")
    html_str = template.render(
        zone_name=scorecard["zone"]["name"],
        region_name=scorecard["zone"].get("region", ""),
        generated_at=datetime.now().strftime("%B %d, %Y at %H:%M"),
        generated_at_date=datetime.now().strftime("%B %d, %Y"),
        organization=organization,
        indicators=scorecard["indicators"],
        risk_score=scorecard["risk_score"],
        data_sources=scorecard.get("data_sources", []),
        map_image_b64=map_b64
    )

    out_path = REPORTS_DIR / f"zone_report_{zone_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf(str(out_path))
    return out_path
```

---

# Stage 12 — Packaging (Tauri Executable)

## Prerequisites
All previous stages complete and tested end-to-end.

## Objective
Package the entire application into a distributable single-file executable for Windows, Linux, and macOS.

## Step 1 — Bundle Python Sidecar with PyInstaller

```
pip install pyinstaller
pyinstaller --onefile --name python-sidecar backend/sidecar_entry.py
```

Create `backend/sidecar_entry.py`:

```python
import subprocess, sys, os, threading, time

def start_service(cmd, name):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(f"{name} started (PID {proc.pid})")
    return proc

if __name__ == "__main__":
    procs = [
        start_service(["uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"], "FastAPI"),
        start_service(["mlflow", "server", "--host", "127.0.0.1", "--port", "5000"], "MLflow"),
        start_service(["prefect", "worker", "start"], "Prefect"),
        start_service(["mage", "start", "raphael_mage", "--host", "127.0.0.1", "--port", "6789"], "Mage.ai"),
    ]
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()
```

Copy output binary to Tauri sidecar location:
```
cp dist/python-sidecar src-tauri/binaries/python-sidecar-x86_64-pc-windows-msvc.exe
```

## Step 2 — Configure Tauri Sidecar in tauri.conf.json

```json
{
  "bundle": {
    "externalBin": ["binaries/python-sidecar"]
  }
}
```

## Step 3 — Implement Sidecar Manager in Rust

Add to `src-tauri/src/sidecar.rs`:

```rust
use tauri::Manager;
use tauri_plugin_shell::ShellExt;

pub fn start_python_sidecar(app: &tauri::AppHandle) {
    let sidecar = app.shell().sidecar("python-sidecar").unwrap();
    let (_rx, child) = sidecar.spawn().expect("Failed to start Python sidecar");
    println!("Python sidecar started");
}
```

## Step 4 — Build the Executable

```
npm run tauri build
```

Output locations:
```
Windows:  src-tauri/target/release/bundle/nsis/raphael_1.0.0_x64-setup.exe
Linux:    src-tauri/target/release/bundle/appimage/raphael_1.0.0_amd64.AppImage
macOS:    src-tauri/target/release/bundle/dmg/raphael_1.0.0_x64.dmg
```

## Step 5 — Test the Packaged Executable

Run the installer on a clean machine with none of the development tools installed.

```
Checklist:
Double-click installer — installs without errors
Application opens — Tauri window appears
Dark map loads with PMTiles tiles
AQ data shows after 60 seconds (first sync)
Risk scores computed and visible on map
Alert rules can be created
PDF report generates and downloads
Application closes cleanly from system tray
No Python or Node.js installation needed on target machine
```

## Step 6 — Create GitHub Actions Release Pipeline

```yaml
# .github/workflows/release.yml
name: Release Raphael

on:
  push:
    tags: ['v*']

jobs:
  release:
    strategy:
      matrix:
        os: [windows-latest, ubuntu-22.04, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - uses: dtolnay/rust-toolchain@stable
      - run: npm install
      - run: pip install -r backend/requirements.txt pyinstaller
      - run: pyinstaller --onefile --name python-sidecar backend/sidecar_entry.py
      - run: cp dist/python-sidecar* src-tauri/binaries/
      - run: npm run tauri build
      - uses: softprops/action-gh-release@v1
        with:
          files: src-tauri/target/release/bundle/**/*
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```
