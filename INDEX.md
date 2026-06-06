# Raphael — Agent Prompt Guide and Stage Index

## How to Use These Documents

This folder contains one prompt file per build stage. Each file is a self-contained instruction set meant to be pasted directly into an AI coding agent such as Cursor, Claude Code, or Windsurf.

The correct workflow is:

```
1. Open your agent
2. Paste the contents of the stage file as your prompt
3. Also attach the relevant docs from the docs/ folder as context
4. Let the agent execute the stage completely
5. Run the verification checklist at the bottom of each stage file
6. Only move to the next stage after all checks pass
```

Never skip stages. Each stage produces artifacts that the next stage depends on.

---

## Context Files to Always Include

Paste or attach these three files as context in every agent session regardless of which stage you are on:

```
docs/SYSTEM_ARCHITECTURE.md      — How every subsystem connects
docs/TECHNICAL_SPECIFICATION.md  — Exact dependency versions and config
docs/DATA_SOURCES.md             — All 28 data sources with endpoints
```

---

## Stage Index

| Stage | File | What It Builds | Duration Estimate |
|---|---|---|---|
| 00 | STAGE_00_ENVIRONMENT.md | System dependencies, API key registrations | 1-2 hours |
| 01 | STAGE_01_SCAFFOLD.md | Tauri + React project structure, all folders | 2-3 hours |
| 02 | STAGE_02_DATABASE.md | PostGIS/SpatiaLite schema, Alembic migrations | 2-3 hours |
| 03 | STAGE_03_API.md | FastAPI with all routes, JWT auth | 3-4 hours |
| 04 | STAGE_04_INGESTION.md | All 24 Prefect data flows, first live sync | 4-6 hours |
| 05 | STAGE_05_RASTER.md | Rasterio LST and NDVI tile processing | 3-4 hours |
| 06 | STAGE_06_ML.md | Prophet forecasting, IsolationForest, risk scores | 3-4 hours |
| 07 | STAGE_07_MAP.md | deck.gl + MapLibre + PMTiles interactive map | 4-6 hours |
| 08 | STAGE_08_TO_12.md | Full dashboard UI, Mage.ai, alerts, reports, packaging | 8-12 hours |

Total estimated build time: 30-42 hours of agent work across sessions.

---

## Stage Dependencies

```
Stage 00 (Environment)
      |
      v
Stage 01 (Scaffold)
      |
      v
Stage 02 (Database)
      |
      v
Stage 03 (FastAPI)
      |
      +----------+----------+
      |          |          |
      v          v          v
  Stage 04   Stage 05   Stage 06
 (Ingestion) (Raster)     (ML)
      |          |          |
      +----------+----------+
                 |
                 v
           Stage 07 (Map)
                 |
                 v
         Stage 08-12 (UI + Packaging)
```

Stages 04, 05, and 06 can be worked on in parallel once Stage 03 is complete.

---

## Agent Prompt Template

Use this template when starting each agent session:

```
You are building Raphael, an urban environmental intelligence desktop application.

Context files attached:
- docs/SYSTEM_ARCHITECTURE.md
- docs/TECHNICAL_SPECIFICATION.md
- docs/DATA_SOURCES.md

Current stage: [STAGE NUMBER AND NAME]

Instructions for this stage are below. Follow them exactly. Use the exact 
dependency versions specified in TECHNICAL_SPECIFICATION.md. Do not substitute 
libraries. Do not skip steps. After completing all steps, confirm each item 
in the verification checklist.

--- PASTE STAGE FILE CONTENTS BELOW THIS LINE ---

[PASTE STAGE FILE HERE]
```

---

## Troubleshooting Common Issues

**GDAL import errors in Python**
GDAL must be installed at the system level before the Python package works. Reinstall system GDAL from Step 5 of Stage 00, then reinstall the Python gdal package with the exact matching version.

**Tauri build fails on Windows**
Ensure Microsoft C++ Build Tools are installed with the Desktop development with C++ workload. Restart the terminal after installation.

**PMTiles map is blank**
The pmtiles protocol handler must be registered in main.tsx before React renders. Check that `maplibregl.addProtocol("pmtiles", protocol.tile)` is called at the module level, not inside a component.

**SpatiaLite mod_spatialite not found**
On Windows, ensure mod_spatialite.dll is in C:\Windows\System32 and not just in the application directory. On Linux, confirm the path with `find / -name "mod_spatialite*" 2>/dev/null`.

**Prophet training fails with insufficient data**
Prophet requires a minimum of 30 observations. Run the ingestion flows manually several times to accumulate enough historical data before running the ML stage.

**FastAPI returns 401 on all requests**
The JWT secret key must be set in the .env file. Generate one with `openssl rand -hex 32` and set it as RAPHAEL_SECRET_KEY.

**deck.gl layers not visible**
Check that the FastAPI CORS middleware includes both `http://localhost:5173` and `tauri://localhost` in allow_origins. Tauri uses a different origin than the browser.

**WeasyPrint PDF generation fails on Windows**
GTK3 runtime must be installed and its bin directory must be on PATH. Restart the terminal after adding to PATH.

**Mage.ai iframe blocked**
Tauri's CSP blocks external iframes by default. Add the following to tauri.conf.json under `app.security`:
```json
{
  "csp": "default-src 'self' http://localhost:6789; frame-src http://localhost:6789"
}
```

---

## Key Ports Reference

| Service | Port | Health Check URL |
|---|---|---|
| React Frontend (dev) | 5173 | http://localhost:5173 |
| FastAPI | 8000 | http://localhost:8000/health |
| MLflow | 5000 | http://localhost:5000/health |
| Prefect | 4200 | http://localhost:4200/health |
| Mage.ai | 6789 | http://localhost:6789/api/status |
| PostgreSQL | 5433 | psql -p 5433 -c "SELECT 1" |

---

## Environment Variables Quick Reference

All variables go in `.env` in the project root.

| Variable | Where to Get It | Required |
|---|---|---|
| EARTHDATA_USERNAME | urs.earthdata.nasa.gov | Yes (for MODIS LST/NDVI) |
| EARTHDATA_PASSWORD | urs.earthdata.nasa.gov | Yes |
| NASA_FIRMS_KEY | firms.modaps.eosdis.nasa.gov | Yes (for fire data) |
| WAQI_API_KEY | aqicn.org/data-platform/token | Yes (for WAQI AQ) |
| IQAIR_API_KEY | iqair.com/dashboard/api | Optional |
| OWM_API_KEY | openweathermap.org/api | Optional |
| SENTINEL_CLIENT_ID | sentinelhub.com | Optional (high-res NDVI) |
| SENTINEL_CLIENT_SECRET | sentinelhub.com | Optional |
| GFW_API_KEY | globalforestwatch.org | Optional |
| RAPHAEL_SECRET_KEY | openssl rand -hex 32 | Yes |
| POSTGRES_PASSWORD | Self-defined | Yes (PostGIS mode) |

Variables marked Optional will cause those specific data sources to be disabled. All other features still work.

---
