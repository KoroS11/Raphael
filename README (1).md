# Raphael — Urban Environmental Intelligence Platform

Raphael is an offline-first, cross-platform desktop application that consolidates urban environmental data into a single interactive intelligence system. It is built entirely on open-source tools and open data sources. The platform collects data from satellite feeds, atmospheric sensors, geospatial APIs, and climate archives, processes and stores it locally, applies machine learning for forecasting and anomaly detection, and presents results through a GPU-accelerated map dashboard designed for non-technical users.

The platform is designed to operate in low-connectivity environments including remote field offices, NGO operations, and municipal bodies in developing regions. It requires no cloud subscription, no paid data provider, and no permanent internet connection. Once data is synchronized, the full feature set operates entirely on the local machine.

---

## Table of Contents

- [Why Raphael Exists](#why-raphael-exists)
- [Core Capabilities](#core-capabilities)
- [Who It Is Built For](#who-it-is-built-for)
- [Technology Foundation](#technology-foundation)
- [Open Data Sources](#open-data-sources)
- [Repository Structure](#repository-structure)
- [Documentation Index](#documentation-index)
- [System Requirements](#system-requirements)
- [Getting Started](#getting-started)
- [License](#license)

---

## Why Raphael Exists

Environmental data about any given city exists in many places. Air quality readings come from one portal, land surface temperature from a satellite archive, vegetation data from another agency, and weather forecasts from yet another source. None of these sources talk to each other. None of them visualize their data spatially. None of them apply predictive models. And almost none of them are accessible to an NGO field worker, a civic planner, or a community activist without significant technical expertise.

Raphael solves this fragmentation problem. It acts as a local intelligence layer that pulls all of this data together, organizes it geospatially, applies forecasting and risk-scoring models, and presents it through an interface that does not require a data science background to interpret.

The core design principle is that environmental intelligence should be available to anyone working on urban sustainability, regardless of their internet connectivity, budget, or technical skill level.

---

## Core Capabilities

**Interactive Map Dashboard**
A full-screen, GPU-accelerated map powered by deck.gl and MapLibre GL. Nine independently toggleable environmental data layers render as spatial heatmaps, 3D column visualizations, and animated point markers directly on the map. A time slider allows historical data to be played back frame by frame across any date range.

**Multi-Layer Environmental Analysis**
Every data layer is independently sourced, processed, and stored. Users can view layers in isolation or in combination. Clicking any point on the map surfaces a detailed data panel for that location across all active layers.

**AI-Powered Forecasting**
Prophet-based time-series models predict air quality and temperature trends 48 to 72 hours ahead. A composite risk score per zone is computed using scikit-learn weighted models combining air quality, land surface temperature, and vegetation density. Isolation Forest anomaly detection flags unusual spikes across any indicator in near real time. MLflow tracks every model version and training run.

**Historical Trend Analysis**
Every data pull is timestamped and stored. Users query any location across any time range for trend charts, month-on-month comparisons, calendar heatmaps, and baseline deviation analysis.

**Alert and Notification System**
Users define threshold-based alert rules per location and indicator. Alerts trigger as system tray notifications even when the application window is closed. All alerts are logged and exportable.

**Zone Comparison**
Up to four geographic zones can be placed side by side. A ranking engine sorts all zones by any indicator. Zone scorecards summarize all environmental dimensions per area.

**Report and PDF Export**
WeasyPrint generates structured, print-ready PDF documents from any combination of map snapshots, trend charts, risk scores, and alert logs. Reports include auto-generated narrative summaries derived from ML output.

**Custom Data Import**
Mage.ai provides a visual pipeline for importing field-collected data in CSV, GeoJSON, KML, Shapefile, and Excel formats. Imported data integrates into the same database and visualization system as API-sourced data.

**Multi-User Access Control**
Local user accounts with four roles: Administrator, Analyst, Field Worker, and Viewer. No cloud authentication required.

**Offline-First Operation**
All data, map tiles via PMTiles, and model outputs are stored locally via PostGIS or SpatiaLite. The application syncs when internet is available and operates fully from the local database when it is not.

---

## Who It Is Built For

**NGO Field Workers**
Identify intervention zones, generate grant reports, track environmental changes over time, receive alerts when conditions deteriorate in areas of concern.

**City Planners and Government Officials**
Monitor multiple zones simultaneously, compare environmental performance across wards or districts, produce evidence-based summaries for planning decisions.

**General Public and Awareness Campaigns**
Understand the environmental condition of a neighborhood, track trends, share data-backed findings with local authorities.

---

## Technology Foundation

Raphael is assembled from established open-source tools. No component is built from scratch where a mature open-source solution exists.

**Desktop Shell**
Tauri v2 produces the native executable for Windows, Linux, and macOS. It manages the lifecycle of all background services and provides system tray integration.

**Frontend**
React with Vite as the build system. deck.gl and Kepler.gl handle all map rendering and data layer visualization. MapLibre GL JS provides the offline-capable base map served from local PMTiles archives. Apache ECharts renders all trend charts and data visualizations. shadcn/ui provides the component system. Framer Motion handles panel transitions. Zustand manages application state. TanStack Query handles all API communication.

**Data Pipeline**
Prefect orchestrates all scheduled data ingestion flows. One flow per data source handles extraction, validation, normalization, and database writes. Mage.ai provides the visual pipeline UI for custom data imports.

**Intelligence Layer**
scikit-learn provides clustering (KMeans), anomaly detection (IsolationForest), and risk scoring. Prophet handles time-series forecasting for air quality and temperature. MLflow tracks all model versions and experiment runs.

**Geospatial Processing**
Rasterio and GDAL process satellite GeoTIFF imagery for NDVI and LST layer derivation. Fiona and GeoPandas handle vector data. pyproj manages coordinate reprojection.

**Database**
PostGIS on PostgreSQL for hardware with 6GB or more RAM. SpatiaLite for hardware below that threshold. Both expose the same spatial SQL interface. The application selects automatically on first launch.

**API**
FastAPI serves all data to the frontend via a local REST interface bound exclusively to localhost.

**Reports**
WeasyPrint renders HTML Jinja2 templates to PDF. Playwright captures map snapshots for embedding in reports.

---

## Open Data Sources

Raphael uses exclusively free, publicly available data. No commercial data subscription is required.

| Category | Sources |
|---|---|
| Air Quality | OpenAQ, WAQI, IQAir AirVisual, CPCB (India), Copernicus CAMS |
| Satellite Imagery | NASA Earthdata MODIS/VIIRS, Copernicus Sentinel-2, USGS Earth Explorer, Google Earth Engine |
| Fire and Heat | NASA FIRMS, NASA LANCE |
| Weather and Climate | Open-Meteo, NOAA GFS, ERA5 via Copernicus CDS, OpenWeatherMap |
| Vegetation | MODIS NDVI, Sentinel-2 NDVI, Global Forest Watch, Hansen Global Forest Change |
| Urban and Geospatial | OpenStreetMap Overpass, GADM, WorldPop, GHSL, NASA SEDAC, Datameet |
| Hazard and Disaster | GDACS, FloodMap, FEMA, EM-DAT, NOAA NCEI |

Full details including endpoints, authentication requirements, update frequencies, and data formats are in `docs/DATA_SOURCES.md`.

---

## Repository Structure

```
raphael/
|-- src-tauri/                     # Tauri desktop shell (Rust)
|   |-- src/
|   |   |-- main.rs
|   |   |-- sidecar.rs             # Service lifecycle manager
|   |   `-- tray.rs                # System tray
|   |-- binaries/                  # Sidecar executables
|   |-- icons/
|   |-- Cargo.toml
|   `-- tauri.conf.json
|
|-- src/                           # React frontend
|   |-- components/
|   |   |-- ui/                    # shadcn base components
|   |   |-- map/                   # deck.gl + MapLibre components
|   |   |-- charts/                # Apache ECharts wrappers
|   |   |-- panels/                # Dashboard panels
|   |   `-- layout/                # Shell layout
|   |-- views/                     # Page-level views
|   |-- store/                     # Zustand stores
|   |-- api/                       # TanStack Query hooks
|   |-- i18n/                      # Translation files (en, hi, mr, fr, sw)
|   |-- types/
|   |-- App.tsx
|   `-- main.tsx
|
|-- backend/                       # Python backend
|   |-- api/                       # FastAPI application
|   |   |-- main.py
|   |   |-- routes/
|   |   |-- models/
|   |   |-- deps.py
|   |   `-- auth.py
|   |-- db/                        # SQLAlchemy + Alembic
|   |   |-- connection.py
|   |   |-- models.py
|   |   |-- queries.py
|   |   `-- migrations/
|   |-- ingestion/                 # Prefect flows
|   |   |-- flows/
|   |   |   |-- aq_openaq.py
|   |   |   |-- aq_waqi.py
|   |   |   |-- aq_iqair.py
|   |   |   |-- aq_cams.py
|   |   |   |-- weather_openmeteo.py
|   |   |   |-- weather_noaa_gfs.py
|   |   |   |-- weather_openweathermap.py
|   |   |   |-- fire_firms.py
|   |   |   |-- fire_lance.py
|   |   |   |-- lst_modis.py
|   |   |   |-- ndvi_sentinel.py
|   |   |   |-- ndvi_modis.py
|   |   |   |-- ndvi_gfw.py
|   |   |   |-- ndvi_hansen.py
|   |   |   |-- boundaries_gadm.py
|   |   |   |-- osm_features.py
|   |   |   |-- urban_ghsl.py
|   |   |   |-- pop_worldpop.py
|   |   |   |-- hazard_gdacs.py
|   |   |   |-- hazard_emdat.py
|   |   |   |-- hazard_noaa_ncei.py
|   |   |   |-- hazard_fema.py
|   |   |   `-- sedac_socioeco.py
|   |   |-- scheduler.py
|   |   `-- base.py
|   |-- processing/
|   |   |-- raster.py              # Rasterio pipelines
|   |   |-- normalize.py
|   |   |-- validate.py
|   |   `-- import_pipeline.py
|   |-- ml/
|   |   |-- forecast.py            # Prophet
|   |   |-- anomaly.py             # IsolationForest
|   |   |-- clustering.py          # KMeans
|   |   |-- risk_score.py
|   |   |-- explainer.py
|   |   `-- runner.py
|   |-- reports/
|   |   |-- generator.py
|   |   |-- renderer.py            # WeasyPrint + Playwright
|   |   |-- templates/
|   |   `-- narrative.py
|   `-- config.py
|
|-- mage/                          # Mage.ai custom import pipelines
|   |-- pipelines/
|   |   |-- csv_import/
|   |   |-- geojson_import/
|   |   |-- kml_import/
|   |   |-- shapefile_import/
|   |   `-- excel_import/
|   `-- custom/
|
|-- config/
|   |-- app.toml
|   |-- datasources.toml
|   `-- ml.toml
|
|-- data/
|   |-- tiles/                     # PMTiles offline map bundles
|   |-- boundaries/                # GADM files
|   `-- raphael.db                 # SpatiaLite database
|
|-- docs/
|   |-- PROJECT_OVERVIEW.md
|   |-- SYSTEM_ARCHITECTURE.md
|   |-- TECHNICAL_SPECIFICATION.md
|   `-- DATA_SOURCES.md
|
|-- scripts/
|   |-- build.sh
|   |-- package.sh
|   `-- seed.py
|
|-- tests/
|-- package.json
|-- vite.config.ts
|-- tsconfig.json
|-- tailwind.config.ts
|-- pyproject.toml
`-- .github/workflows/build.yml
```

---

## Documentation Index

| Document | Description |
|---|---|
| `docs/PROJECT_OVERVIEW.md` | Complete feature module breakdown, user flows, design decisions |
| `docs/SYSTEM_ARCHITECTURE.md` | Subsystem design, data flow diagrams, component interaction, tool configuration |
| `docs/TECHNICAL_SPECIFICATION.md` | Full dependency list, database schema, API contracts, ML specs, build instructions |
| `docs/DATA_SOURCES.md` | All open data sources with endpoints, authentication, coverage, and flow mapping |

---

## System Requirements

**Minimum**
- OS: Windows 10, Ubuntu 20.04, macOS 11
- Processor: Dual-core x86-64, 1.8 GHz
- Memory: 4 GB RAM
- Storage: 10 GB available
- Display: 1280 x 720

**Recommended**
- Processor: Quad-core 2.5 GHz or higher
- Memory: 8 GB RAM
- Storage: 50 GB SSD
- Display: 1920 x 1080

**Network**
- Required only for initial setup and periodic sync
- All features function without network after first sync
- Minimum viable sync requires approximately 200 MB per region per cycle

---

## Getting Started

A demo mode is available on first launch that loads pre-seeded data for a sample region, allowing the full interface to be explored without completing a live sync. Full setup instructions including region selection, API key configuration, and initial data sync are in `docs/PROJECT_OVERVIEW.md`.

---

## License

Raphael is released under the MIT License.
