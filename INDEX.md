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

