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

