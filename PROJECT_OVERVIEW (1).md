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

---

### 4.3 AI Predictions and Forecasting

The forecasting module runs automatically after each data sync and is accessible from the Risk Intelligence section of the sidebar.

**Air Quality Forecast**
A time-series forecasting model is trained on the historical AQ data for the selected region. It produces a 48-hour forward prediction for PM2.5 concentration at each monitoring station location, with an 80% confidence interval band. The output is displayed as a chart with the historical trace on the left and the forecast trace on the right, with the confidence band shown as a shaded region.

**Land Surface Temperature Forecast**
A similar model operates on historical LST data combined with weather forecast inputs. It produces a 72-hour temperature prediction for the region shown as a spatial heatmap snapshot at 6-hour intervals.

**Pollution Spike Prediction**
A classification model scans the AQ forecast output for predicted exceedance events — moments where concentration is forecast to cross a user-defined threshold. These events are surfaced as a timeline of upcoming high-risk windows in the next 24 hours, with the probability of exceedance shown for each.

**Composite Risk Score**
A weighted scoring algorithm computes a 0 to 100 risk score for each geographic zone in the region. The score combines LST, AQ, NDVI, and precipitation inputs using weights that are configurable by the administrator. The score is updated after each intelligence cycle and displayed as a layer on the map and as a card in the city overview panel.

**Anomaly Detection**
An unsupervised anomaly detection model runs continuously on incoming data. It flags readings that deviate significantly from the expected range for that location, time of day, and season. Flagged anomalies trigger alert notifications and appear as marked events on the trend charts.

**Explainability Output**
Every forecast and score is accompanied by a plain-language explanation generated from the model's feature importance output. The explanation lists the top contributing factors and their direction of influence. For example: "Risk score elevated due to land surface temperature 6.2 degrees above seasonal baseline and PM2.5 concentration in the upper quartile for this zone."

---

### 4.4 Alert and Notification System

The alert module operates as a background process and does not require the application window to be open.

**Alert Rule Configuration**
Users create alert rules by specifying a location (either a point, a named zone, or a drawn polygon), an indicator (any of the nine data layers), a comparison operator (above, below, or change by), and a threshold value. Multiple rules can be combined with AND or OR logic. Rules can be scoped to specific time windows such as business hours only or nighttime only.

**Alert Delivery**
When a rule condition is satisfied, a system tray notification appears. The notification includes the rule name, the current value that triggered it, the threshold that was set, and the location. Clicking the notification opens the application window focused on the triggering location.

**Alert Severity**
Rules are assigned a severity level of Informational, Warning, or Critical. The severity determines the color of the notification and its position in the alert log.

**Alert History**
All triggered alerts are stored in the database with full metadata. The alert log view displays all historical alerts with filtering by date range, severity, indicator, and location. The entire log or any filtered subset can be exported as a structured CSV file.

**Scheduled Digest**
A daily or weekly digest view aggregates all alerts from the period into a single summary screen, showing which zones triggered the most alerts, which indicators were most frequently exceeded, and the trend direction for each.

**Geofenced Alerts**
Alert rules can be scoped to a geographic radius around a point. This allows field workers to monitor only the areas relevant to their assignment without being notified about conditions elsewhere in the region.

---

### 4.5 Historical Trend Analysis

All data in Raphael is timestamped at ingestion and retained in the database according to the retention policy set by the administrator. The default retention period is two years.

**Time Series Charts**
Any location can be queried for any indicator over any date range within the retention window. The result is displayed as an interactive line chart with a brushable time axis. Multiple indicators can be overlaid on the same chart with a dual-axis option for indicators with different units.

**Month-on-Month Comparison**
A comparison mode presents the same indicator for the same location across multiple years stacked on the same axis. This allows direct visual comparison of seasonal patterns across years — for example, comparing the PM2.5 profile for Delhi across June of 2022, 2023, and 2024 on a single chart.

**Baseline Analysis**
The user selects a reference period to serve as the baseline — for example, the first three months after a policy change or a tree plantation drive. The system computes the mean and standard deviation of each indicator during that period and plots subsequent readings as deviations from the baseline. This makes it easy to measure the environmental impact of an intervention.

**Calendar Heatmap**
A GitHub-style calendar heatmap displays the daily value of any indicator for any location over the past year. Each cell is color-coded according to the value's position in the observed range. This provides an immediate visual sense of seasonal patterns and anomalous days.

**Correlation Explorer**
A scatter plot view allows two indicators to be plotted against each other for a selected location and date range. A correlation coefficient is computed and displayed. This is used to explore relationships such as the connection between land surface temperature and PM2.5 concentration in a given zone.

**Event Markers**
Users can annotate the time axis with named events — policy changes, interventions, industrial events, natural events, or calendar events like festivals. Event markers appear on all trend charts for the annotated date, allowing visual inspection of whether an event corresponded to a change in environmental indicators.

---

### 4.6 Zone Comparison

The comparison module allows multiple geographic zones to be analyzed side by side.

**Split Map View**
The map panel splits into two independent panels, each displaying a different zone. Layer toggles, time slider, and basemap selection apply independently to each panel. A synchronized mode locks both panels to the same time and zoom level.

**Comparison Table**
A structured table lists all available indicators as rows and all selected zones as columns. Each cell shows the current value, the 30-day trend direction, and a color band indicating severity. Up to four zones can be compared simultaneously.

**Zone Ranking**
The ranking view lists all administrative zones in the region sorted by any chosen indicator. Sorting is available for current value, 30-day change, risk score, and anomaly frequency. The list is color-coded by severity band and can be exported as a table.

**Zone Health Scorecard**
Each zone has a single-page scorecard view that summarizes all indicators, the AI risk score, the most recent alert activity, and the 90-day trend direction for each indicator. The scorecard is designed to be exported as part of a report.

**Intervention Tracking**
If an event marker has been placed in a zone, the scorecard shows a before-and-after comparison of all indicators relative to the event date. This is specifically designed for NGOs tracking the environmental impact of their interventions.

---

### 4.7 Report and PDF Export

The report module generates structured, print-ready PDF documents from any combination of dashboard content.

**Report Types**

Zone Report: A complete environmental snapshot of a single zone. Includes a map image showing the zone with all active layers, a summary scorecard, trend charts for all indicators over the past 30 days, the current risk score with its explanation, and the most recent alerts.

Comparison Report: Side-by-side documentation of two to four zones with a structured comparison table and individual scorecards.

Alert Summary Report: A log of all alerts triggered within a specified date range, formatted as a table with metadata, and a summary section showing the most frequently triggered rules and locations.

Trend Report: A detailed historical analysis of a single location. Includes all trend charts, the baseline deviation analysis, the calendar heatmap, and any event markers with before-and-after comparisons.

Custom Report: The user selects which sections to include from a checklist. Any combination of the above components can be assembled into a single document.

**Report Features**
Reports include the organization name entered during setup, the Raphael version, and the date of generation. All data citations include the source name, the data type, and the timestamp of the most recent sync. Charts and map images are embedded directly. An auto-generated narrative paragraph summarizes the key findings in plain language for each section. Reports are available in A4 format and render cleanly for both digital sharing and print.

---

### 4.8 Custom Data Import

The import module allows externally collected data to be integrated into Raphael's database and visualization system.

**Supported Formats**
- Comma-separated values (CSV) with latitude and longitude columns
- GeoJSON
- Keyhole Markup Language (KML) — the export format of most GPS survey tools
- ESRI Shapefile
- Spreadsheet format (XLSX)

**Import Workflow**
The user selects a file. Raphael reads the file structure and presents a column mapping interface where the user assigns each column to a semantic role — coordinate, timestamp, indicator value, indicator name, unit. Required fields are highlighted. Optional fields can be skipped. A preview of the first ten rows is shown with the mapping applied.

After confirmation, the data is validated. Validation errors are listed per row with the reason for rejection. The user can proceed with valid rows only or correct the file and re-import.

Imported data is stored in the database as a named import dataset. It is available as a data layer on the map, included in trend charts alongside API-sourced data, and eligible for inclusion in reports. Imports can be updated, versioned, or deleted.

---

### 4.9 Multi-User Access Control

**User Roles**

Administrator: Full access to all features, user management, data source configuration, alert rule management, and system settings. Can view activity logs for all users.

Analyst: Access to all data viewing, forecasting, comparison, and export features. Cannot manage users or modify system configuration.

Field Worker: Access to map, alert viewing, zone bookmarking, and report generation. Cannot access raw data exports, custom import, or system settings.

Viewer: Read-only access to the map and dashboard. No export capability.

**Account Management**
User accounts are stored locally in the database. No cloud authentication service is used. The administrator creates and manages accounts from the settings panel. Passwords are stored using a secure one-way hashing algorithm. Session tokens are scoped to the local machine.

**Activity Log**
All significant user actions — report generation, data imports, alert rule changes, user account changes — are recorded in an activity log visible to the administrator. The log is queryable by user, action type, and date range and exportable as a CSV.

---

### 4.10 Settings and Administration

**Sync Configuration**
The administrator sets the sync frequency — hourly, every 6 hours, every 24 hours, or manual only. Individual data sources can be enabled or disabled. A manual sync trigger is always available from the top navigation bar.

**Storage Management**
The storage panel shows the total database size, broken down by data type and date range. The administrator sets a retention policy per data type — for example, keep 2 years of air quality data but only 90 days of raw satellite imagery. A cleanup operation purges data outside the retention window.

**Offline Tile Management**
Downloaded tile bundles are listed with their region name, file size, and last-updated date. Additional regions can be downloaded when internet is available. Unused region tiles can be deleted to recover disk space.

**Backup and Restore**
The entire application database can be exported as a single portable file. This file can be copied to a USB drive and restored on another machine running Raphael. This is the primary mechanism for distributing pre-loaded data to field offices without internet access.

