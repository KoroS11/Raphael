# Raphael — Project Overview

## Document Purpose

This document provides a comprehensive description of the Raphael platform — its purpose, design decisions, feature modules, user flows, and the problems it is built to solve. It is intended for mentors, stakeholders, and new contributors who need a complete understanding of what the system does and why it was designed the way it was.

---

## 1. Problem Statement

Urban environmental data is abundant but inaccessible. Dozens of government agencies, research institutions, and international bodies publish satellite imagery, atmospheric readings, weather models, and vegetation indices as open data. However, these datasets are:

- Scattered across different portals with different formats and access methods
- Presented as raw numbers or downloadable files with no visual interface
- Not integrated with each other, making cross-indicator analysis impossible without programming skills
- Entirely cloud-dependent, breaking access for users in low-connectivity regions
- Designed for technical audiences, not for NGO workers, civic planners, or communities

The result is that the people who most need environmental intelligence — field workers planning interventions, municipal officers making zoning decisions, community groups advocating for change — have no practical way to access it.

Raphael addresses this gap by acting as a local environmental intelligence layer. It pulls data from open sources, integrates it into a unified geospatial database, applies predictive and analytical models, and delivers the results through a visual interface designed for non-technical users. It runs as a standalone desktop application that does not require cloud access, subscriptions, or technical expertise to operate.

---

## 2. Design Principles

**Offline-first**
The system must function completely without internet access after initial data synchronization. This is not a fallback mode — it is the primary design target. Users in low-connectivity regions should have the same experience as users on a stable broadband connection.

**Low hardware requirements**
The system must run on hardware common in NGO and government field offices — machines with 4 GB RAM, dual-core processors, and no dedicated GPU. All computational choices are made with this constraint in mind.

**Data transparency**
Every piece of data shown in the interface must be traceable to its source, its timestamp, and its update frequency. Users should never be left wondering whether a reading is live, cached, or estimated.

**Interpretability over complexity**
Machine learning outputs are always accompanied by a plain-language explanation. A risk score of 78 out of 100 is meaningless without the explanation "High heat combined with poor air quality and low green cover." Every model output in the interface includes this layer of interpretation.

**Designed for the end user, not the analyst**
The default view of any screen is designed for a non-technical user. Advanced controls are available but not visible by default. The interface uses color, spatial visualization, and natural language to communicate environmental conditions rather than raw numbers wherever possible.

---

## 3. System Overview

Raphael is structured as a single packaged desktop application that bundles four internal subsystems:

**Ingestion Subsystem**
Responsible for pulling data from external open sources, validating and normalizing it, and writing it to the local geospatial database. Runs on a configurable schedule. Works incrementally — only new or updated data is fetched on each cycle.

**Intelligence Subsystem**
Reads raw data from the database, applies machine learning models for forecasting, anomaly detection, and risk scoring, and writes the derived outputs back to the database as computed layers. Runs automatically after each ingestion cycle.

**API Subsystem**
A local REST interface that exposes all database content — both raw and computed — to the frontend. All frontend data access goes through this layer. The API is not exposed to any network interface and is accessible only to the application itself.

**Frontend Subsystem**
The user-facing interface. Renders the interactive map, all data layers, charts, dashboards, alert panels, and report generation tools. Reads exclusively from the local API. Does not communicate with any external service directly.

All four subsystems run as managed background processes inside the desktop application shell. The shell starts and monitors them on launch, surfaces their health status in the interface, and terminates them cleanly on exit.

---

## 4. Feature Modules

### 4.1 Onboarding and Region Setup

The first-run experience walks the user through three steps.

**Step 1 — Profile Selection**
The user selects their role from three options: NGO Field Worker, City Planner or Government Official, or General User. The selection determines the default view layout and which features are surfaced prominently. All features remain accessible regardless of role selection.

**Step 2 — Region Configuration**
The user selects their region of interest using one of three methods. They can search for a city or district by name, select from a pre-indexed list of commonly used regions, or draw a custom bounding polygon directly on the map. After selection, the system queries its data availability index to show which data layers are available for that region and at what resolution.

**Step 3 — Initial Sync**
The system downloads the offline map tile bundle for the selected region, pulls the initial batch of environmental data for all available layers, and runs the intelligence subsystem for the first time. A progress interface shows the status of each component download and data pull. The process can be paused and resumed. Once complete, the system transitions to the main dashboard.

A demo mode is available from the first-run screen. It loads pre-seeded data for a sample region and bypasses the sync step entirely, allowing the interface to be explored immediately.

---

### 4.2 Map Explorer

The Map Explorer is the primary interface. It occupies the full center of the application window and is always visible regardless of which secondary panel is open.

**Base Map**
The base map renders from locally stored offline tile bundles. Four basemap styles are available: dark, satellite, light, and terrain. The dark style is the default because it provides the highest contrast for environmental data overlays. Tiles are stored in a single-file format that requires no tile server to serve — they are read directly from disk by the rendering engine.

**Data Layers**
Nine data layers are available, each independently toggleable. The layers panel on the left sidebar lists each layer with a visibility toggle, an opacity slider, and a color legend. Available layers are:

- Land Surface Temperature — rendered as a continuous color gradient heatmap
- Air Quality Index (PM2.5) — rendered as 3D vertical columns, height proportional to concentration
- NDVI Green Cover Index — rendered as a transparency-adjusted green overlay derived from satellite imagery
- Fire and Heat Anomalies — rendered as pulsing point markers at detected anomaly locations
- Precipitation — rendered as a semi-transparent gradient layer
- Urban Density — rendered as a choropleth based on built-up area density
- Risk Score (AI-computed) — rendered as a color-coded zone layer
- Air Quality Monitoring Stations — rendered as clickable point markers with live reading labels
- Administrative Boundaries — rendered as glowing boundary outlines at district or ward level

**Layer Interactions**
Clicking any point on the map opens a location detail panel on the right side showing all active layer values for that point, a 7-day trend sparkline for each indicator, a risk score breakdown, and the timestamp of the most recent data update for each layer.

Drawing a polygon on the map using the selection tool opens a zone summary panel showing aggregate statistics for the selected area across all active layers.

**Time Slider**
A time control bar runs across the top of the map. It spans from 7 days in the past to 30 days in the future. Dragging the handle to a past date replays historical data across all active layers simultaneously. Dragging to a future date switches active layers to their forecast outputs where a model exists. A play button animates the slider automatically.

**Basemap Controls**
A basemap selector in the layer panel provides thumbnail previews of each style. A compass indicator shows current map orientation with a reset-to-north button. A zoom control and a locate-to-region button are fixed on the map edge. The current coordinate, zoom level, and elevation at the map center are displayed at the bottom of the map.

