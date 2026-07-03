# Stage 07 — Interactive Map (deck.gl + MapLibre GL + PMTiles)

## Prerequisites
Stage 06 completed. Risk scores, AQ data, and at least one raster tile exist in the database.

## Objective
Build the full interactive map canvas that occupies the center of the Raphael dashboard. This is the most visually critical stage. The map must exactly replicate the mockup: dark city basemap with glowing neon admin boundaries, the red-orange LST heatmap bleeding across districts, the purple 3D AQ columns rising over pollution hotspots, the pulsing fire anomaly dots, the green NDVI overlay, the clickable AQ station markers with tooltips, and the floating layer panel on the left. Every visual element described below references a specific element visible in the mockup image.

---

## Step 1 — Download Offline Map Tiles (PMTiles)

Create `scripts/download_tiles.py`:

```python
import httpx, os
from pathlib import Path

TILES_DIR = Path(os.getenv("RAPHAEL_DATA_DIR", "./data")) / "tiles"
TILES_DIR.mkdir(parents=True, exist_ok=True)

TILE_SOURCES = {
    "world_base": "https://build.protomaps.com/builds/latest.pmtiles",
    # For India-specific tiles, use Protomaps or self-host from OSM extracts
}

def download_tiles(name: str, url: str):
    out_path = TILES_DIR / f"{name}.pmtiles"
    if out_path.exists():
        print(f"Tiles already exist: {out_path}")
        return
    print(f"Downloading {name} tiles (this may take several minutes)...")
    with httpx.stream("GET", url, timeout=600, follow_redirects=True) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_bytes(8192):
                f.write(chunk)
    print(f"Downloaded: {out_path} ({out_path.stat().st_size / 1e6:.0f} MB)")

if __name__ == "__main__":
    for name, url in TILE_SOURCES.items():
        download_tiles(name, url)
```

Run:
```
python scripts/download_tiles.py
```

---

## Step 2 — Install PMTiles Protocol Handler

Add to `src/main.tsx` before React renders:

```typescript
import { Protocol } from "pmtiles";
import maplibregl from "maplibre-gl";

// Register PMTiles protocol so MapLibre can read local .pmtiles files
const protocol = new Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);
```

---

## Step 3 — Create MapLibre Style Definitions

Create `src/components/map/styles.ts`:

```typescript
import type { StyleSpecification } from "maplibre-gl";

const DATA_DIR = window.__TAURI__
  ? await import("@tauri-apps/api/path").then(m => m.appDataDir())
  : "./data";

export const darkStyle: StyleSpecification = {
  version: 8,
  name: "Raphael Dark",
  sources: {
    protomaps: {
      type: "vector",
      url: `pmtiles://${DATA_DIR}/tiles/world_base.pmtiles`,
      attribution: "Protomaps, OpenStreetMap"
    }
  },
  glyphs: "https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf",
  layers: [
    // Background
    { id: "background", type: "background",
      paint: { "background-color": "#0d1117" }           // Very dark navy
    },
    // Water
    { id: "water", type: "fill", source: "protomaps", "source-layer": "water",
      paint: { "fill-color": "#0a1628" }                // Dark blue
    },
    // Land use
    { id: "landuse-park", type: "fill", source: "protomaps", "source-layer": "landuse",
      filter: ["==", "pmap:kind", "park"],
      paint: { "fill-color": "#0d2318", "fill-opacity": 0.8 }
    },
    // Buildings — very subtle
    { id: "buildings", type: "fill", source: "protomaps", "source-layer": "buildings",
      paint: { "fill-color": "#131d2e", "fill-opacity": 0.9 }
    },
    // Roads — subtle neon traces
    { id: "roads-major", type: "line", source: "protomaps", "source-layer": "roads",
      filter: ["in", "pmap:kind", "primary", "secondary"],
      paint: { "line-color": "#1a2540", "line-width": 1.5 }
    },
    { id: "roads-highway", type: "line", source: "protomaps", "source-layer": "roads",
      filter: ["==", "pmap:kind", "highway"],
      paint: { "line-color": "#0b3d91", "line-width": 2 }
    },
    // City labels
    { id: "city-labels", type: "symbol", source: "protomaps", "source-layer": "places",
      filter: ["==", "pmap:kind", "city"],
      layout: {
        "text-field": ["get", "name"],
        "text-size":  20,
        "text-font":  ["Noto Sans Regular"],
        "text-letter-spacing": 0.15
      },
      paint: {
        "text-color":       "#e0e8ff",
        "text-opacity":     0.6,
        "text-halo-color":  "rgba(0,0,0,0.5)",
        "text-halo-width":  1
      }
    }
  ]
};

export const satelliteStyle: StyleSpecification = {
  version: 8,
  name: "Raphael Satellite",
  sources: {
    satellite: {
      type: "raster",
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      tileSize: 256
    }
  },
  layers: [{ id: "satellite", type: "raster", source: "satellite" }]
};

export const lightStyle: StyleSpecification = {
  version: 8,
  name: "Raphael Light",
  sources: {
    protomaps: {
      type: "vector",
      url: `pmtiles://${DATA_DIR}/tiles/world_base.pmtiles`
    }
  },
  glyphs: "https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf",
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#f8fafc" } },
    { id: "water", type: "fill", source: "protomaps", "source-layer": "water",
      paint: { "fill-color": "#bfdbfe" } },
    { id: "buildings", type: "fill", source: "protomaps", "source-layer": "buildings",
      paint: { "fill-color": "#e2e8f0" } },
    { id: "roads", type: "line", source: "protomaps", "source-layer": "roads",
      paint: { "line-color": "#94a3b8", "line-width": 1 } }
  ]
};

export const styles = { dark: darkStyle, satellite: satelliteStyle, light: lightStyle };
```

---

## Step 4 — Create deck.gl Layer Definitions

Create `src/components/map/layers.ts`:

```typescript
import {
  HeatmapLayer, ColumnLayer, BitmapLayer,
  ScatterplotLayer, GeoJsonLayer, IconLayer, ScreenGridLayer
} from "@deck.gl/layers";

// AQI color scale matching mockup (purple 3D columns)
const AQI_COLOR_SCALE = [
  [0,   228, 0],    // Good       0-50    green
  [255, 255, 0],    // Moderate   51-100  yellow
  [255, 126, 0],    // Unhealthy  101-150 orange
  [255, 0,   0],    // Unhealthy  151-200 red
  [143, 63,  151],  // Very Poor  201-300 purple  ← matches mockup
  [126, 0,   35],   // Hazardous  301+    maroon
];

function aqiColor(value: number): [number, number, number, number] {
  if (value <= 50)  return [0,   228, 0,   200];
  if (value <= 100) return [255, 255, 0,   200];
  if (value <= 150) return [255, 126, 0,   200];
  if (value <= 200) return [255, 0,   0,   200];
  if (value <= 300) return [143, 63,  151, 220];
  return               [126, 0,   35,  255];
}

export function buildAQLayer(data: GeoJSON.FeatureCollection, visible: boolean, opacity: number) {
  const points = data.features.map(f => ({
    position:     [f.geometry.coordinates[0], f.geometry.coordinates[1]] as [number,number],
    elevation:    (f.properties?.value ?? 0) * 0.8,
    color:        aqiColor(f.properties?.value ?? 0),
    station_name: f.properties?.station_name ?? "",
    value:        f.properties?.value ?? 0,
    aqi:          f.properties?.aqi ?? 0,
  }));

  return new ColumnLayer({
    id:              "aq-column-layer",
    data:            points,
    visible,
    opacity,
    diskResolution:  12,
    radius:          350,
    elevationScale:  1,
    getPosition:     d => d.position,
    getElevation:    d => d.elevation,
    getFillColor:    d => d.color,
    pickable:        true,
    autoHighlight:   true,
    highlightColor:  [255, 255, 255, 60],
  });
}

export function buildLSTLayer(data: GeoJSON.FeatureCollection, visible: boolean, opacity: number) {
  return new HeatmapLayer({
    id:          "lst-heatmap-layer",
    data:        data.features.map(f => ({
      position: [f.geometry.coordinates[0], f.geometry.coordinates[1]] as [number,number],
      weight:   (f.properties?.value ?? 20) / 50
    })),
    visible,
    opacity,
    radiusPixels: 50,
    intensity:    1.5,
    threshold:    0.03,
    // Color range: blue -> cyan -> yellow -> orange -> red (matching mockup)
    colorRange: [
      [0,   0,   255, 0],
      [0,   255, 255, 100],
      [255, 255, 0,   180],
      [255, 128, 0,   220],
      [255, 0,   0,   255],
    ],
    getPosition: d => d.position,
    getWeight:   d => d.weight,
  });
}

export function buildNDVILayer(
  tileUrl: string,
  bounds: [number,number,number,number],
  visible: boolean,
  opacity: number
) {
  return new BitmapLayer({
    id:      "ndvi-bitmap-layer",
    visible,
    opacity,
    bounds,  // [west, south, east, north]
    image:   tileUrl,
    pickable: false,
  });
}

export function buildFireLayer(data: GeoJSON.FeatureCollection, visible: boolean, opacity: number) {
  const pulseTime = Date.now() % 2000 / 2000; // 0-1 pulse cycle
  const pulseRadius = 300 + pulseTime * 200;   // Expanding ring effect

  return new ScatterplotLayer({
    id:            "fire-scatter-layer",
    data:          data.features.map(f => ({
      position:  [f.geometry.coordinates[0], f.geometry.coordinates[1]] as [number,number],
      value:     f.properties?.value ?? 1,
      name:      f.properties?.station_name ?? "Fire Anomaly"
    })),
    visible,
    opacity,
    pickable:        true,
    stroked:         true,
    filled:          true,
    radiusMinPixels: 6,
    radiusMaxPixels: 20,
    lineWidthMinPixels: 2,
    getPosition:     d => d.position,
    getRadius:       d => 400 + (d.value * 50),
    getFillColor:    [255, 60, 0, 200],
    getLineColor:    [255, 200, 0, 255],
    getLineWidth:    2,
  });
}

export function buildBoundaryLayer(
  data: GeoJSON.FeatureCollection,
  visible: boolean,
  riskScores: Record<string, number>
) {
  return new GeoJsonLayer({
    id:      "admin-boundary-layer",
    data,
    visible,
    pickable:       true,
    stroked:        true,
    filled:         true,
    lineWidthMinPixels: 1,
    // Neon blue-white outline — matching mockup
    getLineColor:   [0, 180, 255, 200],
    getLineWidth:   2,
    // Fill with very subtle risk tint
    getFillColor:   (f: any) => {
      const score = riskScores[f.properties?.id] ?? 0;
      if (score >= 85) return [255, 0,   0,   30];
      if (score >= 70) return [255, 128, 0,   20];
      if (score >= 50) return [255, 255, 0,   15];
      return                  [0,   200, 100, 10];
    },
    autoHighlight:  true,
    highlightColor: [255, 255, 255, 30],
  });
}

export function buildAQStationLayer(
  data: GeoJSON.FeatureCollection,
  visible: boolean
) {
  return new IconLayer({
    id:       "aq-station-icon-layer",
    data:     data.features.map(f => ({
      position:     [f.geometry.coordinates[0], f.geometry.coordinates[1]] as [number,number],
      station_name: f.properties?.station_name ?? "",
      value:        f.properties?.value ?? 0,
      aqi:          f.properties?.aqi ?? 0,
      category:     f.properties?.aqi_category ?? "",
    })),
    visible,
    pickable:        true,
    iconAtlas:       "/icons/station-atlas.png",
    iconMapping:     "/icons/station-atlas.json",
    getIcon:         () => "station",
    getSize:         28,
    getPosition:     d => d.position,
    getColor:        d => aqiColor(d.value),
    sizeScale:       1,
    billboard:       true,
  });
}

export function buildUrbanDensityLayer(
  data: GeoJSON.FeatureCollection,
  visible: boolean,
  opacity: number
) {
  return new ScreenGridLayer({
    id:          "urban-density-layer",
    data:        data.features.map(f => ({
      position: [f.geometry.coordinates[0], f.geometry.coordinates[1]] as [number,number],
      weight:   f.properties?.value ?? 1
    })),
    visible,
    opacity,
    cellSizePixels: 20,
    colorRange:     [
      [18,  18,  18,  0],
      [30,  40,  80,  100],
      [50,  80,  160, 180],
      [80,  120, 220, 220],
      [100, 160, 255, 255],
    ],
    getPosition: d => d.position,
    getWeight:   d => d.weight,
  });
}
```

---

## Step 5 — Create the Map Canvas Component

Create `src/components/map/MapCanvas.tsx`:

```typescript
import { useEffect, useRef, useState, useCallback } from "react";
import { DeckGL } from "@deck.gl/react";
import Map from "react-map-gl/maplibre";
import { motion, AnimatePresence } from "framer-motion";
import { useMapStore } from "../../store/mapStore";
import { useDataStore } from "../../store/dataStore";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  buildAQLayer, buildLSTLayer, buildNDVILayer, buildFireLayer,
  buildBoundaryLayer, buildAQStationLayer, buildUrbanDensityLayer
} from "./layers";
import { LocationDetailPanel } from "../panels/LocationDetailPanel";
import { CoordinateBar } from "./CoordinateBar";
import { MapControls } from "./MapControls";
import { darkStyle, satelliteStyle, lightStyle } from "./styles";
import "maplibre-gl/dist/maplibre-gl.css";

const INITIAL_VIEW = {
  longitude: 77.2090,
  latitude:  28.6139,
  zoom:      10,
  pitch:     30,          // Slight tilt for 3D column effect
  bearing:   0,
};

const STYLE_MAP: Record<string, any> = {
  dark:      darkStyle,
  satellite: satelliteStyle,
  light:     lightStyle,
};

export function MapCanvas() {
  const { activeLayers, layerOpacity, basemap, timePosition } = useMapStore();
  const { activeRegion } = useDataStore();
  const [viewState,       setViewState]       = useState(INITIAL_VIEW);
  const [clickedLocation, setClickedLocation] = useState<{lat:number,lon:number}|null>(null);
  const [tooltip,         setTooltip]         = useState<{x:number,y:number,content:any}|null>(null);
  const deckRef = useRef<any>(null);

  const bbox = `${viewState.longitude - 0.3},${viewState.latitude - 0.3},${viewState.longitude + 0.3},${viewState.latitude + 0.3}`;

  // Fetch layer data from FastAPI
  const { data: aqData }       = useQuery({ queryKey: ["layer","aq",bbox],       queryFn: () => api.getLayer("aq",       activeRegion, bbox) });
  const { data: fireData }     = useQuery({ queryKey: ["layer","fire",bbox],      queryFn: () => api.getLayer("fire",     activeRegion, bbox) });
  const { data: boundaryData } = useQuery({ queryKey: ["boundaries",activeRegion], queryFn: () => api.getZones(activeRegion) });
  const { data: riskData }     = useQuery({ queryKey: ["risk",activeRegion],      queryFn: () => api.getRiskScores(activeRegion) });
  const { data: lstBounds }    = useQuery({ queryKey: ["tile-bounds","lst"],      queryFn: () => api.getTileBounds("lst", activeRegion) });

  const riskScoreMap = Object.fromEntries(
    (riskData?.data?.features ?? []).map((f:any) => [f.properties.zone_id, f.properties.risk_score])
  );

  const lstTileUrl  = `http://localhost:8000/api/v1/layers/lst/tile?region_id=${activeRegion}`;
  const ndviTileUrl = `http://localhost:8000/api/v1/layers/ndvi/tile?region_id=${activeRegion}`;

  // Build deck.gl layers
  const layers = [
    activeLayers.includes("urban") && buildUrbanDensityLayer(aqData?.data, true, layerOpacity.urban ?? 0.6),
    activeLayers.includes("lst")   && buildLSTLayer(aqData?.data ?? {type:"FeatureCollection",features:[]}, true, layerOpacity.lst ?? 0.7),
    activeLayers.includes("ndvi")  && lstBounds?.data && buildNDVILayer(ndviTileUrl, lstBounds.data.bounds, true, layerOpacity.ndvi ?? 0.65),
    activeLayers.includes("boundaries") && boundaryData?.data && buildBoundaryLayer(boundaryData.data, true, riskScoreMap),
    activeLayers.includes("aq")    && aqData?.data && buildAQLayer(aqData.data, true, layerOpacity.aq ?? 1.0),
    activeLayers.includes("fire")  && fireData?.data && buildFireLayer(fireData.data, true, layerOpacity.fire ?? 1.0),
    activeLayers.includes("stations") && aqData?.data && buildAQStationLayer(aqData.data, true),
  ].filter(Boolean);

  const onHover = useCallback(({ object, x, y }: any) => {
    if (object) {
      setTooltip({ x, y, content: object });
    } else {
      setTooltip(null);
    }
  }, []);

  const onClick = useCallback(({ coordinate, object }: any) => {
    if (coordinate) {
      setClickedLocation({ lon: coordinate[0], lat: coordinate[1] });
    }
  }, []);

  return (
    <div className="relative w-full h-full bg-[#0d1117]">
      <DeckGL
        ref={deckRef}
        viewState={viewState}
        onViewStateChange={({ viewState: vs }: any) => setViewState(vs)}
        controller={{ dragPan: true, scrollZoom: true, touchZoom: true }}
        layers={layers}
        onHover={onHover}
        onClick={onClick}
        getTooltip={({ object }: any) => null}
      >
        <Map
          mapStyle={STYLE_MAP[basemap] ?? darkStyle}
          attributionControl={false}
        />
      </DeckGL>

      {/* Floating tooltip */}
      <AnimatePresence>
        {tooltip && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="absolute z-20 pointer-events-none"
            style={{ left: tooltip.x + 12, top: tooltip.y - 40 }}
          >
            <MapTooltip content={tooltip.content} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Location detail panel */}
      <AnimatePresence>
        {clickedLocation && (
          <motion.div
            initial={{ x: 300, opacity: 0 }}
            animate={{ x: 0,   opacity: 1 }}
            exit={{ x: 300,    opacity: 0 }}
            transition={{ type: "spring", damping: 25 }}
            className="absolute right-0 top-0 bottom-0 w-72 z-10"
          >
            <LocationDetailPanel
              lat={clickedLocation.lat}
              lon={clickedLocation.lon}
              onClose={() => setClickedLocation(null)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <MapControls onZoomIn={() => setViewState(v => ({...v, zoom: v.zoom + 1}))}
                   onZoomOut={() => setViewState(v => ({...v, zoom: v.zoom - 1}))}
                   onNorth={() => setViewState(v => ({...v, bearing: 0}))}
                   on3D={() => setViewState(v => ({...v, pitch: v.pitch > 0 ? 0 : 45}))}
                   currentPitch={viewState.pitch} />

      <CoordinateBar
        lat={viewState.latitude}
        lon={viewState.longitude}
        zoom={viewState.zoom}
      />
    </div>
  );
}

function MapTooltip({ content }: { content: any }) {
  const props = content?.properties ?? content;
  if (!props) return null;

  // AQ station tooltip — matches mockup popup style
  if (props.station_name && props.aqi !== undefined) {
    return (
      <div className="bg-[#0d1117]/90 border border-blue-500/30 rounded-lg px-3 py-2 text-sm backdrop-blur-sm min-w-[160px]">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
          <span className="font-medium text-white">{props.station_name}</span>
        </div>
        <div className="text-blue-200 text-xs">AQI {props.aqi}</div>
        <div className="text-gray-400 text-xs">{props.category}</div>
      </div>
    );
  }

  // Fire anomaly tooltip — matches mockup
  if (props.name?.includes("Fire") || props.layer_type === "fire") {
    return (
      <div className="bg-red-950/90 border border-red-500/40 rounded-lg px-3 py-2 text-sm">
        <div className="font-medium text-red-200">Heat Anomaly</div>
        <div className="text-red-400 text-xs">High Intensity</div>
      </div>
    );
  }

  // Zone / boundary tooltip
  if (props.zone_name || props.name) {
    return (
      <div className="bg-[#0d1117]/90 border border-white/10 rounded-lg px-3 py-2 text-sm">
        <div className="font-medium text-white">{props.zone_name ?? props.name}</div>
        {props.risk_score && (
          <div className="text-orange-400 text-xs">Risk Score: {props.risk_score}/100</div>
        )}
      </div>
    );
  }

  return null;
}
```

---

## Step 6 — Create the Layers Panel

This is the left-side panel in the mockup with all toggleable layers and opacity sliders.

Create `src/components/map/LayersPanel.tsx`:

```typescript
import { Switch } from "../ui/switch";
import { Slider } from "../ui/slider";
import { useMapStore } from "../../store/mapStore";
import { motion } from "framer-motion";
import { X } from "lucide-react";

const LAYER_DEFINITIONS = [
  { id: "lst",        label: "Land Surface Temp",   color: "#ff4444", icon: "🌡" },
  { id: "aq",         label: "Air Quality (PM2.5)",  color: "#a855f7", icon: "💨" },
  { id: "ndvi",       label: "NDVI (Green Cover)",   color: "#22c55e", icon: "🌿" },
  { id: "fire",       label: "Fire / Heat Anomalies",color: "#ef4444", icon: "🔥" },
  { id: "precipitation", label: "Precipitation",    color: "#3b82f6", icon: "🌧" },
  { id: "urban",      label: "Urban Density",        color: "#f59e0b", icon: "🏙" },
  { id: "risk",       label: "Risk Score (AI)",      color: "#f97316", icon: "⚠" },
  { id: "stations",   label: "AQ Stations",          color: "#06b6d4", icon: "📍" },
  { id: "boundaries", label: "Admin Boundaries",     color: "#64748b", icon: "🗺" },
];

const BASEMAP_OPTIONS = [
  { id: "dark",      label: "Dark",      preview: "bg-gray-950" },
  { id: "satellite", label: "Satellite", preview: "bg-emerald-950" },
  { id: "light",     label: "Light",     preview: "bg-gray-100"  },
  { id: "terrain",   label: "Terrain",   preview: "bg-yellow-900" },
];

export function LayersPanel({ onClose }: { onClose: () => void }) {
  const { activeLayers, layerOpacity, basemap, toggleLayer, setOpacity, setBasemap } = useMapStore();

  return (
    <motion.div
      initial={{ x: -280, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -280, opacity: 0 }}
      transition={{ type: "spring", damping: 25 }}
      className="absolute left-0 top-0 z-10 w-72 bg-[#0a0f1a]/95 border-r border-white/10 h-full backdrop-blur-md flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <span className="text-sm font-semibold text-white">Layers</span>
        <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
          <X size={16} />
        </button>
      </div>

      {/* Layer toggles */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        {LAYER_DEFINITIONS.map(layer => {
          const isActive = activeLayers.includes(layer.id);
          const opacity  = layerOpacity[layer.id] ?? 1.0;

          return (
            <div key={layer.id} className="rounded-lg px-3 py-2 hover:bg-white/5 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: layer.color }}
                  />
                  <span className="text-xs text-gray-300 font-medium">{layer.label}</span>
                </div>
                <Switch
                  checked={isActive}
                  onCheckedChange={() => toggleLayer(layer.id)}
                  className="scale-75"
                />
              </div>
              {isActive && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  className="mt-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-12">Opacity</span>
                    <Slider
                      value={[opacity * 100]}
                      onValueChange={([v]) => setOpacity(layer.id, v / 100)}
                      max={100} min={10} step={5}
                      className="flex-1"
                    />
                    <span className="text-xs text-gray-500 w-8">{Math.round(opacity * 100)}%</span>
                  </div>
                </motion.div>
              )}
            </div>
          );
        })}
      </div>

      {/* Basemap selector */}
      <div className="px-3 py-3 border-t border-white/10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Basemap</span>
        </div>
        <div className="grid grid-cols-4 gap-2">
          {BASEMAP_OPTIONS.map(opt => (
            <button
              key={opt.id}
              onClick={() => setBasemap(opt.id)}
              className={`
                flex flex-col items-center gap-1 p-1.5 rounded-lg border transition-all
                ${basemap === opt.id
                  ? "border-blue-400 bg-blue-400/10"
                  : "border-white/10 hover:border-white/30"
                }
              `}
            >
              <div className={`w-full h-8 rounded ${opt.preview} border border-white/10`} />
              <span className="text-xs text-gray-400">{opt.label}</span>
            </button>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
```

---

## Step 7 — Create Zustand Map Store

Create `src/store/mapStore.ts`:

```typescript
import { create } from "zustand";

interface MapStore {
  activeLayers:  string[];
  layerOpacity:  Record<string, number>;
  basemap:       string;
  timePosition:  number;  // 0 = -7days, 1 = now, 2 = +30days
  toggleLayer:   (id: string) => void;
  setOpacity:    (id: string, value: number) => void;
  setBasemap:    (style: string) => void;
  setTime:       (value: number) => void;
}

export const useMapStore = create<MapStore>((set) => ({
  activeLayers: ["lst", "aq", "ndvi", "fire", "boundaries", "stations"],
  layerOpacity: {
    lst:         0.70,
    aq:          1.00,
    ndvi:        0.65,
    fire:        1.00,
    boundaries:  0.80,
    urban:       0.50,
    precipitation: 0.60,
    risk:        0.70,
    stations:    1.00,
  },
  basemap:      "dark",
  timePosition: 1,

  toggleLayer: (id) =>
    set(state => ({
      activeLayers: state.activeLayers.includes(id)
        ? state.activeLayers.filter(l => l !== id)
        : [...state.activeLayers, id]
    })),

  setOpacity: (id, value) =>
    set(state => ({ layerOpacity: { ...state.layerOpacity, [id]: value } })),

  setBasemap: (style) => set({ basemap: style }),
  setTime:    (value) => set({ timePosition: value }),
}));
```

---

## Verification Checklist

```
MapCanvas renders without React errors
Dark basemap visible (not blank white)
PMTiles source loads from local file (check network tab - no external tile requests)
AQ ColumnLayer shows purple 3D columns over AQ station locations
LST HeatmapLayer shows temperature gradient
Admin boundary outlines visible as neon blue strokes
Clicking a map point opens LocationDetailPanel on the right
Hovering over AQ column shows station tooltip matching mockup style
LayersPanel toggles turn layers on and off correctly
Opacity slider changes layer transparency in real time
Basemap selector switches between dark, satellite, light
Coordinate bar shows correct lat/lon as map pans
```
