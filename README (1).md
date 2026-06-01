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
