# Raphael — System Architecture

## Document Purpose

This document defines the complete technical architecture of Raphael. Every subsystem, the open-source tool powering it, data flows between components, and interaction contracts between layers are specified here. This is the authoritative reference for implementation.

---

## 1. High-Level Architecture

Raphael is a locally-deployed desktop application composed of six distinct subsystems bundled into a single executable. All subsystems run as managed background processes inside the Tauri desktop shell.

```
+================================================================================================+
|                                  RAPHAEL DESKTOP APPLICATION                                  |
|                                        (Tauri v2 Shell)                                        |
|                                                                                                |
|  +---------------------------+  +---------------------------+  +---------------------------+  |
|  |      FRONTEND UI          |  |     LOCAL REST API        |  |   CUSTOM IMPORT UI        |  |
|  |                           |  |                           |  |                           |  |
|  |  React 18 + Vite 5        |  |  FastAPI (port 8000)      |  |  Mage.ai (port 6789)      |  |
|  |  deck.gl / Kepler.gl      |  |  Pydantic models          |  |  Visual pipeline builder  |  |
|  |  MapLibre GL JS           |  |  JWT auth middleware      |  |  Column mapper            |  |
|  |  Apache ECharts           |  |  SQLAlchemy ORM           |  |  Format validator         |  |
|  |  shadcn/ui                |<->|  GeoAlchemy2              |  |  CSV / GeoJSON / KML      |  |
|  |  Framer Motion            |  |  Alembic migrations       |  |  Shapefile / Excel        |  |
|  |  Zustand                  |  |                           |  |                           |  |
|  |  TanStack Query           |  +---------------------------+  +---------------------------+  |
|  |  PMTiles (offline tiles)  |             |                             |                    |
|  |  (port 5173)              |             v                             v                    |
|  +---------------------------+  +--------------------------------------------------+         |
|                                 |           GEOSPATIAL DATABASE                    |         |
|                                 |                                                  |         |
|                                 |  PostGIS (RAM >= 6GB)  OR  SpatiaLite (< 6GB)   |         |
|                                 |  GIST spatial indexes                            |         |
|                                 |  Alembic schema migrations                       |         |
|                                 |  Single portable .db file (SpatiaLite mode)      |         |
|                                 +--------------------------------------------------+         |
|                                              |                                               |
|                   +--------------------------+---------------------------+                   |
|                   |                                                      |                   |
|  +----------------+----------------+    +--------------------------------+-------------+     |
|  |     DATA INGESTION              |    |        INTELLIGENCE LAYER                    |     |
|  |                                 |    |                                              |     |
|  |  Prefect OSS (port 4200)        |    |  scikit-learn (KMeans, IsolationForest)      |     |
|  |  One flow per data source       |    |  Prophet (time-series forecasting)           |     |
|  |  Retry + backoff logic          |    |  MLflow (model tracking, port 5000)          |     |
|  |  Incremental sync               |    |  Rasterio + GDAL (raster processing)         |     |
|  |  Offline-aware scheduling       |    |  GeoPandas + Fiona (vector processing)       |     |
|  |  24 active flows                |    |  NumPy + SciPy (band math, statistics)       |     |
|  +---------------------------------+    +----------------------------------------------+     |
|                                                                                                |
+================================================================================================+
                                            |
                         (internet connection, when available)
                                            |
     +--------------------------------------+--------------------------------------+
     |                     |                |                |                    |
+----------+       +---------------+  +----------+  +-------------+  +------------------+
| AIR      |       | SATELLITE &   |  | WEATHER  |  | GEOSPATIAL  |  | HAZARD &         |
| QUALITY  |       | IMAGERY       |  | CLIMATE  |  | BOUNDARIES  |  | DISASTER         |
|          |       |               |  |          |  |             |  |                  |
| OpenAQ   |       | NASA FIRMS    |  | Open-    |  | GADM        |  | GDACS            |
| WAQI     |       | NASA MODIS    |  | Meteo    |  | OSM Overpass|  | FloodMap/FEMA    |
| IQAir    |       | Sentinel-2    |  | NOAA GFS |  | WorldPop    |  | NASA LANCE       |
| CPCB     |       | USGS Landsat  |  | ERA5 CDS |  | GHSL        |  | EM-DAT           |
| Cop.CAMS |       | Google EE     |  | OpenWthr |  | NASA SEDAC  |  | NOAA NCEI        |
|          |       | NASA LANCE    |  |          |  | Datameet    |  |                  |
+----------+       +---------------+  +----------+  +-------------+  +------------------+
```

---

## 2. Desktop Shell — Tauri v2

Tauri v2 is the outermost layer. It produces the native executable, manages all background service lifecycles, and bridges the frontend to the host operating system.

### 2.1 Service Launch Sequence

```
raphael.exe starts
      |
      v
Tauri Shell initializes
      |
      +---> Detect available RAM
      |         |
      |         +-- >= 6GB --> Launch PostgreSQL + PostGIS sidecar (port 5433)
      |         +-- <  6GB --> Initialize SpatiaLite .db file (no server process)
      |
      +---> Run Alembic migrations (schema up to date check)
      |
      +---> Start FastAPI server                    (port 8000)
      |         +--> GET /health check, wait for 200
      |
      +---> Start MLflow tracking server            (port 5000)
      |         +--> GET /health check, wait for 200
      |
      +---> Start Prefect worker                    (port 4200)
      |         +--> Register all 24 scheduled flows
      |         +--> Run initial sync if first launch
      |
      +---> Start Mage.ai server                    (port 6789)
      |         +--> GET /api/status check, wait for 200
      |
      +---> Load React frontend                     (port 5173)
      |         +--> Open Tauri window to localhost:5173
      |
      v
All services healthy --> Dashboard renders
Any service fails   --> Error overlay with service name + restart button
```

### 2.2 Sidecar Binary Layout

```
src-tauri/binaries/
|-- postgress-sidecar-x86_64-pc-windows-msvc.exe
|-- postgress-sidecar-x86_64-unknown-linux-gnu
|-- postgress-sidecar-aarch64-apple-darwin
|-- python-sidecar-x86_64-pc-windows-msvc.exe
|-- python-sidecar-x86_64-unknown-linux-gnu
`-- python-sidecar-aarch64-apple-darwin
