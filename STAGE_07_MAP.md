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
