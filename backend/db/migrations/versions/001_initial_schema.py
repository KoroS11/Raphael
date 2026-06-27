"""initial_schema

Revision ID: 001
Revises: 
Create Date: 2026-06-01 00:11:51.935063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check current dialect to dynamically switch between PostgreSQL and SQLite/SpatiaLite schemas
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        # PostGIS Schema
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        
        op.execute("""
        CREATE TABLE users (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username        VARCHAR(100) UNIQUE NOT NULL,
            password_hash   TEXT NOT NULL,
            display_name    VARCHAR(200),
            role            VARCHAR(20) NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'analyst', 'field_worker', 'viewer')),
            organization    VARCHAR(200),
            preferred_language CHAR(5) DEFAULT 'en',
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            last_active_at  TIMESTAMPTZ
        );
        """)

        op.execute("""
        CREATE TABLE activity_log (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID REFERENCES users(id),
            action          VARCHAR(100) NOT NULL,
            resource_type   VARCHAR(50),
            resource_id     UUID,
            metadata        JSONB,
            performed_at    TIMESTAMPTZ DEFAULT NOW()
        );
        """)

        op.execute("""
        CREATE TABLE regions (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            VARCHAR(200) NOT NULL,
            country_code    CHAR(3) NOT NULL,
            bbox            geometry(Polygon, 4326) NOT NULL,
            admin_level     INT DEFAULT 2,
            pmtiles_path    TEXT,
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            is_active       BOOLEAN DEFAULT false
        );
        """)
        op.execute("CREATE INDEX idx_regions_bbox ON regions USING GIST(bbox);")

        op.execute("""
        CREATE TABLE sources (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key             VARCHAR(50) UNIQUE NOT NULL,
            name            VARCHAR(200) NOT NULL,
            category        VARCHAR(50) NOT NULL,
            layer_types     JSONB NOT NULL,
            base_url        TEXT,
            is_enabled      BOOLEAN DEFAULT true,
            last_synced_at  TIMESTAMPTZ,
            last_error      TEXT,
            error_count     INT DEFAULT 0
        );
        """)

        op.execute("""
        CREATE TABLE raw_observations (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_id       UUID NOT NULL REFERENCES sources(id),
            region_id       UUID NOT NULL REFERENCES regions(id),
            layer_type      VARCHAR(50) NOT NULL,
            geometry        geometry(Point, 4326) NOT NULL,
            value           FLOAT NOT NULL,
            unit            VARCHAR(20),
            station_id      VARCHAR(100),
            station_name    VARCHAR(200),
            observed_at     TIMESTAMPTZ NOT NULL,
            synced_at       TIMESTAMPTZ DEFAULT NOW(),
            raw_payload     JSONB,
            is_anomalous    BOOLEAN DEFAULT false,
            anomaly_score   FLOAT
        );
        """)
        op.execute("CREATE INDEX idx_raw_obs_layer_region   ON raw_observations(layer_type, region_id);")
        op.execute("CREATE INDEX idx_raw_obs_observed_at    ON raw_observations(observed_at DESC);")
        op.execute("CREATE INDEX idx_raw_obs_geometry       ON raw_observations USING GIST(geometry);")
        op.execute("CREATE INDEX idx_raw_obs_station        ON raw_observations(station_id);")
        op.execute("CREATE INDEX idx_raw_obs_source         ON raw_observations(source_id);")

        op.execute("""
        CREATE TABLE zone_geometries (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            region_id       UUID NOT NULL REFERENCES regions(id),
            admin_level     INT NOT NULL,
            name            VARCHAR(200) NOT NULL,
            name_local      VARCHAR(200),
            gadm_gid        VARCHAR(100),
            geometry        geometry(MultiPolygon, 4326) NOT NULL,
            properties      JSONB,
            source          VARCHAR(50) DEFAULT 'gadm'
        );
        """)
        op.execute("CREATE INDEX idx_zones_region   ON zone_geometries(region_id);")
        op.execute("CREATE INDEX idx_zones_geometry ON zone_geometries USING GIST(geometry);")

        op.execute("""
        CREATE TABLE raster_tiles (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            layer_type      VARCHAR(50) NOT NULL,
            region_id       UUID NOT NULL REFERENCES regions(id),
            source_id       UUID REFERENCES sources(id),
            tile_path       TEXT NOT NULL,
            bounds          geometry(Polygon, 4326),
            processed_at    TIMESTAMPTZ DEFAULT NOW(),
            valid_date      DATE NOT NULL,
            resolution_m    INT,
            colormap        VARCHAR(50) DEFAULT 'plasma'
        );
        """)
        op.execute("CREATE INDEX idx_raster_layer_region ON raster_tiles(layer_type, region_id);")
        op.execute("CREATE INDEX idx_raster_valid_date   ON raster_tiles(valid_date DESC);")

        op.execute("""
        CREATE TABLE ml_outputs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            zone_id         UUID REFERENCES zone_geometries(id),
            geometry        geometry(Point, 4326),
            model_type      VARCHAR(50) NOT NULL,
            output_type     VARCHAR(50) NOT NULL,
            layer_type      VARCHAR(50),
            value           FLOAT NOT NULL,
            confidence_lower FLOAT,
            confidence_upper FLOAT,
            explanation     TEXT,
            model_version   VARCHAR(50),
            mlflow_run_id   VARCHAR(100),
            computed_at     TIMESTAMPTZ DEFAULT NOW(),
            valid_from      TIMESTAMPTZ,
            valid_to        TIMESTAMPTZ
        );
        """)
        op.execute("CREATE INDEX idx_ml_type        ON ml_outputs(model_type, output_type);")
        op.execute("CREATE INDEX idx_ml_zone        ON ml_outputs(zone_id);")
        op.execute("CREATE INDEX idx_ml_valid       ON ml_outputs(valid_from, valid_to);")
        op.execute("CREATE INDEX idx_ml_computed    ON ml_outputs(computed_at DESC);")

        op.execute("""
        CREATE TABLE alert_rules (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID NOT NULL REFERENCES users(id),
            name            VARCHAR(200) NOT NULL,
            layer_type      VARCHAR(50) NOT NULL,
            geometry        geometry(Geometry, 4326),
            zone_id         UUID REFERENCES zone_geometries(id),
            operator        VARCHAR(20) NOT NULL CHECK (operator IN ('gt', 'lt', 'change_gt', 'change_lt')),
            threshold       FLOAT NOT NULL,
            severity        VARCHAR(20) NOT NULL DEFAULT 'warning' CHECK (severity IN ('info', 'warning', 'critical')),
            time_window     JSONB,
            radius_km       FLOAT,
            is_active       BOOLEAN DEFAULT true,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        """)

        op.execute("""
        CREATE TABLE alert_events (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rule_id         UUID NOT NULL REFERENCES alert_rules(id),
            triggered_at    TIMESTAMPTZ DEFAULT NOW(),
            observed_value  FLOAT NOT NULL,
            location        geometry(Point, 4326),
            acknowledged    BOOLEAN DEFAULT false,
            acknowledged_at TIMESTAMPTZ,
            acknowledged_by UUID REFERENCES users(id)
        );
        """)
        op.execute("CREATE INDEX idx_alert_events_rule      ON alert_events(rule_id);")
        op.execute("CREATE INDEX idx_alert_events_triggered ON alert_events(triggered_at DESC);")

        op.execute("""
        CREATE TABLE import_datasets (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID NOT NULL REFERENCES users(id),
            name            VARCHAR(200) NOT NULL,
            format          VARCHAR(20) NOT NULL CHECK (format IN ('csv', 'geojson', 'kml', 'shapefile', 'excel')),
            row_count       INT,
            schema_map      JSONB NOT NULL,
            layer_type      VARCHAR(50),
            mage_pipeline_id VARCHAR(100),
            imported_at     TIMESTAMPTZ DEFAULT NOW(),
            is_visible      BOOLEAN DEFAULT true
        );
        """)

        op.execute("""
        CREATE TABLE event_markers (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID NOT NULL REFERENCES users(id),
            name            VARCHAR(200) NOT NULL,
            description     TEXT,
            zone_id         UUID REFERENCES zone_geometries(id),
            geometry        geometry(Geometry, 4326),
            event_date      DATE NOT NULL,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        """)

    else:
        # SQLite / SpatiaLite Schema
        op.execute("""
        CREATE TABLE users (
            id              TEXT PRIMARY KEY,
            username        TEXT UNIQUE NOT NULL,
            password_hash   TEXT NOT NULL,
            display_name    TEXT,
            role            TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'analyst', 'field_worker', 'viewer')),
            organization    TEXT,
            preferred_language TEXT DEFAULT 'en',
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_active_at  DATETIME
        );
        """)

        op.execute("""
        CREATE TABLE activity_log (
            id              TEXT PRIMARY KEY,
            user_id         TEXT REFERENCES users(id),
            action          TEXT NOT NULL,
            resource_type   TEXT,
            resource_id     TEXT,
            metadata        TEXT,
            performed_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        op.execute("""
        CREATE TABLE regions (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            country_code    TEXT NOT NULL,
            admin_level     INTEGER DEFAULT 2,
            pmtiles_path    TEXT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active       BOOLEAN DEFAULT 0
        );
        """)
        # bbox added via AddGeometryColumn
        op.execute("SELECT AddGeometryColumn('regions', 'bbox', 4326, 'POLYGON', 'XY');")
        op.execute("SELECT CreateSpatialIndex('regions', 'bbox');")

        op.execute("""
        CREATE TABLE sources (
            id              TEXT PRIMARY KEY,
            key             TEXT UNIQUE NOT NULL,
            name            TEXT NOT NULL,
            category        TEXT NOT NULL,
            layer_types     TEXT NOT NULL,
            base_url        TEXT,
            is_enabled      BOOLEAN DEFAULT 1,
            last_synced_at  DATETIME,
            last_error      TEXT,
            error_count     INTEGER DEFAULT 0
        );
        """)

        op.execute("""
        CREATE TABLE raw_observations (
            id              TEXT PRIMARY KEY,
            source_id       TEXT NOT NULL REFERENCES sources(id),
            region_id       TEXT NOT NULL REFERENCES regions(id),
            layer_type      TEXT NOT NULL,
            value           REAL NOT NULL,
            unit            TEXT,
            station_id      TEXT,
            station_name    TEXT,
            observed_at     DATETIME NOT NULL,
            synced_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
            raw_payload     TEXT,
            is_anomalous    BOOLEAN DEFAULT 0,
            anomaly_score   REAL
        );
        """)
        # geometry added via AddGeometryColumn
        op.execute("SELECT AddGeometryColumn('raw_observations', 'geometry', 4326, 'POINT', 'XY');")
        op.execute("SELECT CreateSpatialIndex('raw_observations', 'geometry');")

        op.execute("CREATE INDEX idx_raw_obs_layer_region   ON raw_observations(layer_type, region_id);")
        op.execute("CREATE INDEX idx_raw_obs_observed_at    ON raw_observations(observed_at);")
        op.execute("CREATE INDEX idx_raw_obs_station        ON raw_observations(station_id);")
        op.execute("CREATE INDEX idx_raw_obs_source         ON raw_observations(source_id);")

        op.execute("""
        CREATE TABLE zone_geometries (
            id              TEXT PRIMARY KEY,
            region_id       TEXT NOT NULL REFERENCES regions(id),
            admin_level     INTEGER NOT NULL,
            name            TEXT NOT NULL,
            name_local      TEXT,
            gadm_gid        TEXT,
            properties      TEXT,
            source          TEXT DEFAULT 'gadm'
        );
        """)
        # geometry added via AddGeometryColumn
        op.execute("SELECT AddGeometryColumn('zone_geometries', 'geometry', 4326, 'MULTIPOLYGON', 'XY');")
        op.execute("SELECT CreateSpatialIndex('zone_geometries', 'geometry');")
        
        op.execute("CREATE INDEX idx_zones_region   ON zone_geometries(region_id);")

        op.execute("""
        CREATE TABLE raster_tiles (
            id              TEXT PRIMARY KEY,
            layer_type      TEXT NOT NULL,
            region_id       TEXT NOT NULL REFERENCES regions(id),
            source_id       TEXT REFERENCES sources(id),
            tile_path       TEXT NOT NULL,
            processed_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            valid_date      DATE NOT NULL,
            resolution_m    INTEGER,
            colormap        TEXT DEFAULT 'plasma'
        );
        """)
        # bounds added via AddGeometryColumn
        op.execute("SELECT AddGeometryColumn('raster_tiles', 'bounds', 4326, 'POLYGON', 'XY');")
        op.execute("SELECT CreateSpatialIndex('raster_tiles', 'bounds');")
        
        op.execute("CREATE INDEX idx_raster_layer_region ON raster_tiles(layer_type, region_id);")
        op.execute("CREATE INDEX idx_raster_valid_date   ON raster_tiles(valid_date);")

        op.execute("""
        CREATE TABLE ml_outputs (
            id              TEXT PRIMARY KEY,
            zone_id         TEXT REFERENCES zone_geometries(id),
            model_type      TEXT NOT NULL,
            output_type     TEXT NOT NULL,
            layer_type      TEXT,
            value           REAL NOT NULL,
            confidence_lower REAL,
            confidence_upper REAL,
            explanation     TEXT,
            model_version   TEXT,
            mlflow_run_id   TEXT,
            computed_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            valid_from      DATETIME,
            valid_to        DATETIME
        );
        """)
        # geometry added via AddGeometryColumn
        op.execute("SELECT AddGeometryColumn('ml_outputs', 'geometry', 4326, 'POINT', 'XY');")
        op.execute("SELECT CreateSpatialIndex('ml_outputs', 'geometry');")

        op.execute("CREATE INDEX idx_ml_type        ON ml_outputs(model_type, output_type);")
        op.execute("CREATE INDEX idx_ml_zone        ON ml_outputs(zone_id);")
        op.execute("CREATE INDEX idx_ml_valid       ON ml_outputs(valid_from, valid_to);")
        op.execute("CREATE INDEX idx_ml_computed    ON ml_outputs(computed_at);")

        op.execute("""
        CREATE TABLE alert_rules (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL REFERENCES users(id),
            name            TEXT NOT NULL,
            layer_type      TEXT NOT NULL,
            zone_id         TEXT REFERENCES zone_geometries(id),
            operator        TEXT NOT NULL CHECK (operator IN ('gt', 'lt', 'change_gt', 'change_lt')),
            threshold       REAL NOT NULL,
            severity        TEXT NOT NULL DEFAULT 'warning' CHECK (severity IN ('info', 'warning', 'critical')),
            time_window     TEXT,
            radius_km       REAL,
            is_active       BOOLEAN DEFAULT 1,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # geometry added via AddGeometryColumn
        op.execute("SELECT AddGeometryColumn('alert_rules', 'geometry', 4326, 'GEOMETRY', 'XY');")
        op.execute("SELECT CreateSpatialIndex('alert_rules', 'geometry');")

        op.execute("""
        CREATE TABLE alert_events (
            id              TEXT PRIMARY KEY,
            rule_id         TEXT NOT NULL REFERENCES alert_rules(id),
            triggered_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            observed_value  REAL NOT NULL,
            acknowledged    BOOLEAN DEFAULT 0,
            acknowledged_at DATETIME,
            acknowledged_by TEXT REFERENCES users(id)
        );
        """)
        # location added via AddGeometryColumn
        op.execute("SELECT AddGeometryColumn('alert_events', 'location', 4326, 'POINT', 'XY');")
        op.execute("SELECT CreateSpatialIndex('alert_events', 'location');")

        op.execute("CREATE INDEX idx_alert_events_rule      ON alert_events(rule_id);")
        op.execute("CREATE INDEX idx_alert_events_triggered ON alert_events(triggered_at);")

        op.execute("""
        CREATE TABLE import_datasets (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL REFERENCES users(id),
            name            TEXT NOT NULL,
            format          TEXT NOT NULL CHECK (format IN ('csv', 'geojson', 'kml', 'shapefile', 'excel')),
            row_count       INTEGER,
            schema_map      TEXT NOT NULL,
            layer_type      TEXT,
            mage_pipeline_id TEXT,
            imported_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_visible      BOOLEAN DEFAULT 1
        );
        """)

        op.execute("""
        CREATE TABLE event_markers (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL REFERENCES users(id),
            name            TEXT NOT NULL,
            description     TEXT,
            zone_id         TEXT REFERENCES zone_geometries(id),
            event_date      DATE NOT NULL,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # geometry added via AddGeometryColumn
        op.execute("SELECT AddGeometryColumn('event_markers', 'geometry', 4326, 'GEOMETRY', 'XY');")
        op.execute("SELECT CreateSpatialIndex('event_markers', 'geometry');")


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    tables = [
        "activity_log",
        "event_markers",
        "import_datasets",
        "alert_events",
        "alert_rules",
        "ml_outputs",
        "raster_tiles",
        "raw_observations",
        "zone_geometries",
        "regions",
        "sources",
        "users"
    ]

    if dialect_name == "postgresql":
        for table in tables:
            op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
    else:
        # For SpatiaLite SQLite, clean up geometry columns and drop tables
        for table in tables:
            # We can drop tables directly, but to be safe we drop them
            op.execute(f"DROP TABLE IF EXISTS {table};")
        
        # Clean up spatial metadata references for dropped tables
        op.execute("DELETE FROM geometry_columns WHERE f_table_name IN ('regions', 'raw_observations', 'zone_geometries', 'raster_tiles', 'ml_outputs', 'alert_rules', 'alert_events', 'event_markers');")
        op.execute("DELETE FROM sqlite_sen_geometry_columns WHERE f_table_name IN ('regions', 'raw_observations', 'zone_geometries', 'raster_tiles', 'ml_outputs', 'alert_rules', 'alert_events', 'event_markers');")
