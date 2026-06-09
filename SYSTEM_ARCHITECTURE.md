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
```

The Python sidecar bundles FastAPI, Prefect, MLflow, Mage.ai, scikit-learn, Prophet, Rasterio, and all dependencies into a single self-contained binary using PyInstaller. The frontend is embedded as a static asset bundle inside the Tauri binary.

---

## 3. Frontend — deck.gl + MapLibre + React

### 3.1 Rendering Stack

```
Browser Canvas (WebGL 2.0)
        |
        v
deck.gl 8.x rendering engine
        |
        +---> DeckGL React component
        |           |
        |           +--> HeatmapLayer        (LST - temperature gradient)
        |           +--> ColumnLayer          (AQ PM2.5 - 3D hexagons)
        |           +--> BitmapLayer          (NDVI - GeoTIFF overlay)
        |           +--> ScatterplotLayer     (Fire/heat anomalies - pulsing dots)
        |           +--> GeoJsonLayer         (Admin boundaries - neon outlines)
        |           +--> IconLayer            (AQ monitoring stations)
        |           +--> PolygonLayer         (Risk score zones - color coded)
        |           +--> ScreenGridLayer      (Urban density - GHSL)
        |           `-- ArcLayer             (Wind vectors - optional)
        |
        +---> MapLibre GL JS 4.x (base map)
                    |
                    +--> PMTiles protocol handler
                    |     +--> Reads tile data directly from local .pmtiles file
                    |     +--> No tile server process required
                    |     +--> HTTP range requests to local filesystem
                    |
                    +--> Style definitions (dark / satellite / light / terrain)
                    `-- Offline-capable after PMTiles bundle downloaded
```

### 3.2 Layer Rendering Specifications

```
HEATMAP LAYER — Land Surface Temperature (MODIS / Sentinel)
------------------------------------------------------------
deck.gl:        HeatmapLayer
Data source:    GET /api/v1/layers/lst/current
Color scale:    [0,0,255] (20C) -> [255,255,0] (35C) -> [255,0,0] (50C+)
Radius pixels:  30 (auto-adjusts with zoom)
Intensity:      1.0
Aggregation:    MEAN

COLUMN LAYER — Air Quality PM2.5 (OpenAQ / WAQI / IQAir)
----------------------------------------------------------
deck.gl:        ColumnLayer
Data source:    GET /api/v1/layers/aq/current
Color scale:    AQI category colors (Good=green, Moderate=yellow,
                Unhealthy=orange, Very Unhealthy=red, Hazardous=purple)
Elevation:      value * 500 (1 ug/m3 = 500 units height)
Radius:         400 meters
Pickable:       true

BITMAP LAYER — NDVI Green Cover (Sentinel-2 / MODIS / GFW)
------------------------------------------------------------
deck.gl:        BitmapLayer
Data source:    Rasterio-processed PNG tile path from raster_tiles table
Bounds:         Region bounding box [west, south, east, north]
Opacity:        0.65 (user-adjustable via layer panel slider)
Colormap:       Applied server-side during raster processing

SCATTER LAYER — Fire and Heat Anomalies (NASA FIRMS / LANCE)
-------------------------------------------------------------
deck.gl:        ScatterplotLayer
Data source:    GET /api/v1/layers/fire/current
Color:          [255, 50, 0, 200] pulsing animation via Framer Motion
Radius:         500 meters
Pickable:       true (click shows FRP value + confidence)

GEOJSON LAYER — Administrative Boundaries (GADM / Datameet)
------------------------------------------------------------
deck.gl:        GeoJsonLayer
Data source:    GET /api/v1/zones
Stroke color:   [0, 180, 255, 180] (neon blue-white)
Fill:           Transparent (or risk score choropleth when risk layer active)
Line width:     2px
Highlight:      true on hover

SCREEN GRID LAYER — Urban Density (GHSL / WorldPop)
----------------------------------------------------
deck.gl:        ScreenGridLayer
Data source:    GET /api/v1/layers/urban/current
Cell size:      20 pixels
Color range:    [Low density gray] -> [High density orange]

ICON LAYER — AQ Monitoring Stations (OpenAQ / WAQI / CPCB)
------------------------------------------------------------
deck.gl:        IconLayer
Data source:    GET /api/v1/layers/aq/stations
Icon:           Custom SVG station marker
Size:           24px
Pickable:       true (click shows full station data panel)
Label:          AQI value rendered alongside icon
```

### 3.3 Offline Map Tile Architecture

```
PMTiles Bundle Strategy
-----------------------

Global bundle (zoom 0-5):     world_base.pmtiles       (~50 MB)
Country bundle (zoom 0-10):   {country_iso}.pmtiles     (~200-800 MB)
City bundle (zoom 0-16):      {city_slug}.pmtiles       (~80-300 MB)

India examples:
  india_base.pmtiles           ~600 MB  (country, zoom 0-10)
  delhi_city.pmtiles           ~120 MB  (city, zoom 0-16)
  mumbai_city.pmtiles          ~180 MB  (city, zoom 0-16)

MapLibre configuration:
  protocol: "pmtiles"
  source: "pmtiles://${APP_DATA}/tiles/${region}.pmtiles"
  No tile server. No CDN. No network required after download.
```

### 3.4 Frontend Component Tree

```
App (React 18)
|
|-- Shell
|   |-- TitleBar (Tauri custom titlebar)
|   |-- Sidebar
|   |   |-- RaphaelLogo
|   |   |-- NavLinks
|   |   |   |-- Explorer
|   |   |   |-- Dashboard
|   |   |   |-- Map Explorer
|   |   |   |-- Live Monitoring
|   |   |   |-- Risk Intelligence
|   |   |   |-- Analytics
|   |   |   |-- Alerts
|   |   |   |-- Reports
|   |   |   |-- Data Catalog
|   |   |   `-- Settings
|   |   |-- UserProfile
|   |   `-- SystemStatusIndicator (all 5 services)
|   |
|   `-- TopBar
|       |-- SearchBox (location search)
|       |-- RegionSelector
|       |-- TimeSlider (-7D to +30D, Kepler.gl timeline component)
|       |-- CompareButton
|       |-- ExportButton
|       `-- NotificationBell (alert count badge)
|
|-- Views
|   |-- ExplorerView
|   |   |-- MapCanvas
|   |   |   |-- MapLibreBase (PMTiles dark style)
|   |   |   |-- DeckGLOverlay (all layer instances)
|   |   |   |-- MapControls (zoom, compass, locate, 3D toggle)
|   |   |   `-- CoordinateBar (lat, lon, zoom, elevation)
|   |   |-- LayersPanel (left sidebar)
|   |   |   |-- LayerToggle x9 (visibility + opacity slider each)
|   |   |   |-- ColorLegend per active layer
|   |   |   `-- BasemapSelector (dark, satellite, light, terrain thumbnails)
|   |   `-- LocationDetailPanel (right sidebar, on map click)
|   |       |-- IndicatorCards (all layers at clicked point)
|   |       |-- SparklineChart (ECharts, 7-day trend per indicator)
|   |       `-- RiskScoreBreakdown (gauge + contribution bars)
|   |
|   |-- DashboardView
|   |   |-- CityOverviewCard (region name, weather, overall status)
|   |   |-- MetricCards (AQI, LST, NDVI, Risk Score — color coded)
|   |   |-- RecentAlertsList (last 3 triggered alerts)
|   |   |-- AQITrendChart (ECharts 7-day line chart)
|   |   `-- BottomPanelRow
|   |       |-- LiveAQStationsPanel (top 5 stations table)
|   |       |-- LSTThumbnailPanel (rasterio PNG mini-map)
|   |       |-- NDVIThumbnailPanel (rasterio PNG mini-map)
|   |       |-- PrecipitationChart (ECharts bar chart, Open-Meteo data)
|   |       |-- WindWeatherPanel (ECharts radar + compass SVG)
|   |       `-- AIInsightsPanel (3 auto-generated insight cards from ML)
|   |
|   |-- RiskIntelligenceView
|   |   |-- RiskMapPanel (deck.gl choropleth from ml_outputs)
|   |   |-- ForecastChartPanel (Prophet output, ECharts with confidence band)
|   |   |-- AnomalyLogPanel (IsolationForest flagged events)
|   |   `-- ExplainabilityPanel (plain-language ML output)
|   |
|   |-- AnalyticsView
|   |   |-- TimeSeriesChart (ECharts, any indicator, any range)
|   |   |-- CalendarHeatmap (ECharts heatmap, GitHub-style)
|   |   |-- CorrelationScatter (ECharts scatter, two indicators)
|   |   `-- BaselineDeviationChart (ECharts with event markers)
|   |
|   |-- ComparisonView
|   |   |-- SplitMapPanel (two deck.gl instances side by side)
|   |   |-- ComparisonTable (zones x indicators grid)
|   |   |-- ZoneRankingList (sortable, color-coded)
|   |   `-- ZoneScorecardPanel (full zone summary)
|   |
|   |-- AlertsView
|   |   |-- AlertRuleBuilder (form: zone + indicator + operator + threshold)
|   |   |-- ActiveRulesList
|   |   `-- AlertHistoryLog (filterable, exportable CSV)
|   |
|   |-- ReportsView
|   |   |-- ReportTypeSelector (Zone / Comparison / Alert / Trend / Custom)
|   |   |-- ReportConfigPanel
|   |   |-- GenerationStatusPanel (Prefect task progress)
|   |   `-- ReportHistoryList (download completed PDFs)
|   |
|   |-- DataCatalogView
|   |   |-- ImportWizard (Mage.ai embedded iframe on port 6789)
|   |   |-- ImportDatasetList
|   |   `-- DataSourceStatusGrid (sync status per source)
|   |
|   `-- SettingsView
|       |-- SyncConfigPanel (Prefect schedule config)
|       |-- StorageManagerPanel (DB size, retention policy)
|       |-- TileManagerPanel (PMTiles bundles)
|       |-- UserManagementPanel
|       |-- LanguageSelector (i18next)
|       `-- BackupRestorePanel
```

---

## 4. Data Ingestion — Prefect OSS

### 4.1 Flow Architecture

Prefect runs as a local worker process. All 24 flows follow the same pattern:

```
Prefect scheduler triggers flow
            |
            v
    +-------------------+
    | Check connectivity |---> Offline --> Log skip, mark for retry
    +-------------------+
            |
            v
    +-------------------+
    | Fetch from source  |---> HTTP error --> Retry x3 (exponential backoff)
    +-------------------+
            |
            v
    +-------------------+
    | Validate schema    |---> Mismatch --> Log warning, skip batch, alert admin
    +-------------------+
            |
            v
    +-------------------+
    | Normalize + dedup  |
    | Reproject CRS      |
    | Apply scale factors|
    +-------------------+
            |
            v
    +-------------------+
    | Bulk write to DB   |---> Error --> Rollback transaction, alert
    +-------------------+
            |
            v
    +-------------------+
    | Signal ML runner   |
    +-------------------+
```

### 4.2 Complete Flow Inventory

```
backend/ingestion/flows/
|
|-- AIR QUALITY (3 flows)
|   |-- aq_openaq.py           OpenAQ v3 API          Every 1 hour
|   |-- aq_waqi.py             World AQI API           Every 1 hour
|   |-- aq_iqair.py            IQAir AirVisual API     Every 1 hour
|   `-- aq_cams.py             Copernicus CAMS         Every 6 hours
|
|-- WEATHER (3 flows)
|   |-- weather_openmeteo.py   Open-Meteo API          Every 1 hour
|   |-- weather_noaa_gfs.py    NOAA GFS model          Every 6 hours
|   `-- weather_openweathermap.py  OpenWeatherMap API  Every 1 hour
|
|-- FIRE AND HEAT (2 flows)
|   |-- fire_firms.py          NASA FIRMS VIIRS        Every 3 hours
|   `-- fire_lance.py          NASA LANCE NRT          Every 3 hours
|
|-- SATELLITE IMAGERY (4 flows)
|   |-- lst_modis.py           NASA MODIS MOD11A1      Daily
|   |-- ndvi_modis.py          NASA MODIS MOD13A2      Every 16 days
|   |-- ndvi_sentinel.py       Copernicus Sentinel-2   Every 5 days
|   `-- imagery_usgs.py        USGS Earth Explorer     On demand
|
|-- VEGETATION (2 flows)
|   |-- ndvi_gfw.py            Global Forest Watch API Every 7 days
|   `-- ndvi_hansen.py         Hansen Forest Change    Annual
|
|-- GEOSPATIAL AND URBAN (5 flows)
|   |-- boundaries_gadm.py     GADM boundaries         One-time per region
|   |-- osm_features.py        OSM Overpass API        Every 7 days
|   |-- urban_ghsl.py          GHSL built-up layer     Annual
|   |-- pop_worldpop.py        WorldPop density        Annual
|   `-- sedac_socioeco.py      NASA SEDAC              Annual
|
|-- HAZARD AND DISASTER (5 flows)
|   |-- hazard_gdacs.py        GDACS RSS feed          Every 1 hour
|   |-- hazard_fema.py         FEMA flood zones        Every 30 days
|   |-- hazard_emdat.py        EM-DAT database         Every 7 days
|   |-- hazard_noaa_ncei.py    NOAA NCEI events        Every 7 days
|   `-- hazard_lance.py        NASA LANCE hazards      Every 3 hours
```

### 4.3 Raster Processing Pipeline (Rasterio + GDAL)

```
GeoTIFF arrives from NASA / Copernicus
            |
            v
rasterio.open() reads file metadata
            |
            v
Check CRS -- if not EPSG:4326 --> pyproj reproject
            |
            v
Clip to region bounding box (rasterio.mask)
            |
            v
Apply band math:
  NDVI = (B08 - B04) / (B08 + B04)      [Sentinel-2]
  LST  = (raw_value * 0.02) - 273.15    [MODIS Kelvin to Celsius]
            |
            v
numpy.clip() to valid range
            |
            v
Apply matplotlib colormap to array --> RGBA PNG
            |
            v
Write PNG to data/tiles/{layer}_{region}_{date}.png
            |
            v
Write tile metadata to raster_tiles table
            |
            v
FastAPI serves tile path to frontend BitmapLayer
```

---

## 5. Intelligence Layer

### 5.1 Tool Stack

| Task | Tool | Details |
|---|---|---|
| Time-series forecast | Prophet (Meta) | AQ + temperature, 48-72h ahead |
| Anomaly detection | scikit-learn IsolationForest | All layers, rolling 7-day window |
| Zone clustering | scikit-learn KMeans | 5 clusters, weekly refit |
| Risk scoring | scikit-learn MinMaxScaler + weighted sum | All zones, after every sync |
| Model tracking | MLflow | All runs logged, versioned |
| Raster analytics | Rasterio + NumPy | Band math, zonal statistics |
| Vector analytics | GeoPandas | Zone aggregation, spatial joins |

### 5.2 Intelligence Run Sequence

```
Triggered after every ingestion cycle OR manual request
                        |
                        v
            Read new observations from DB
            (PostGIS spatial query per layer per zone)
                        |
            +-----------+-----------+-----------+
            |           |           |           |
            v           v           v           v
      IsolationForest  KMeans   Prophet      Risk Score
      Anomaly detect   Zone     Retrain if   Compute all
      (all layers)     cluster  >= 10 new    zones with
            |          update   obs          MinMaxScaler
            |           |           |           |
            +-----------+-----------+-----------+
                        |
                        v
            Generate explainability text
            (feature importance -> f-string template)
                        |
                        v
            Write all outputs to ml_outputs table
                        |
                        v
            Log experiment to MLflow (port 5000)
                        |
                        v
            Invalidate FastAPI response cache
```

---

## 6. Custom Import — Mage.ai

Mage.ai runs as a local web process on port 6789. It is embedded in the Raphael Data Catalog view as an iframe. It handles the visual import pipeline for field-collected data.

```
Mage.ai Pipeline per Format
----------------------------

CSV Import Pipeline:
  Block 1 (Data Loader):   Read CSV with pandas
  Block 2 (Transformer):   Column mapper (user-defined in UI)
  Block 3 (Transformer):   Validate lat/lon, parse timestamps, check units
  Block 4 (Transformer):   Reproject coordinates if needed
  Block 5 (Data Exporter): Write to raw_observations table via SQLAlchemy

GeoJSON Import Pipeline:
  Block 1:  Read GeoJSON with Fiona
  Block 2:  Extract geometry + properties
  Block 3:  Validate geometry type and CRS
  Block 4:  Map properties to observation schema
  Block 5:  Write to database

KML Import Pipeline:
  Block 1:  Parse KML with xml.etree
  Block 2:  Extract Placemark coordinates + extended data
  Block 3:  Validate and normalize
  Block 4:  Write to database

Shapefile Import Pipeline:
  Block 1:  Read .shp with GeoPandas
  Block 2:  Reproject to EPSG:4326
  Block 3:  Extract attribute columns
  Block 4:  Map to observation schema
  Block 5:  Write to database

Excel Import Pipeline:
  Block 1:  Read .xlsx with openpyxl
  Block 2:  Column mapper
  Block 3:  Validate
  Block 4:  Write to database
```

---

## 7. Report Generation Pipeline

```
User configures report (type + sections + date range + zones)
                    |
                    v
POST /api/v1/reports/generate
                    |
                    v
FastAPI queues Prefect background task
                    |
                    v
        +-----------+-----------+
        |                       |
        v                       v
Playwright headless          Fetch all chart data
browser captures             from PostGIS via
deck.gl map as PNG           SQLAlchemy queries
(at configured time              |
 position + active layers)       v
        |                   Render ECharts to SVG
        |                   using pyecharts
        |                   (server-side Python)
        +-----------+-----------+
                    |
                    v
        Generate narrative text
        (Jinja2 template + ML explainability output)
                    |
                    v
        Assemble full HTML document
        (Jinja2 template engine)
                    |
                    v
        WeasyPrint HTML -> PDF render
        (A4, print-ready, embedded fonts)
                    |
                    v
        Write to data/reports/{uuid}.pdf
                    |
                    v
GET /api/v1/reports/{id}/download returns PDF binary
```

---

## 8. Complete Data Flow

### 8.1 Write Path (Ingestion Cycle)

