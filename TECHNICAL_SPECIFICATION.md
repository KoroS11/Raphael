# Raphael — Technical Specification

## Document Purpose

This is the implementation-level specification for every component of Raphael. It covers the complete dependency list, configuration files, database schema, API contracts, ML model parameters, and build instructions. Any agent or developer implementing Raphael should treat this as the ground truth for what to build and how to build it.

---

## 1. Complete Dependency List

### 1.1 Frontend — package.json

```json
{
  "name": "raphael-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "tauri": "tauri"
  },
  "dependencies": {
    "@deck.gl/core": "^8.9.0",
    "@deck.gl/layers": "^8.9.0",
    "@deck.gl/react": "^8.9.0",
    "@deck.gl/aggregation-layers": "^8.9.0",
    "@deck.gl/geo-layers": "^8.9.0",
    "@kepler.gl/components": "^3.0.0",
    "@kepler.gl/reducers": "^3.0.0",
    "@kepler.gl/actions": "^3.0.0",
    "maplibre-gl": "^4.0.0",
    "pmtiles": "^3.0.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "echarts": "^5.5.0",
    "echarts-for-react": "^3.0.2",
    "framer-motion": "^11.0.0",
    "@tanstack/react-query": "^5.0.0",
    "@tanstack/react-query-devtools": "^5.0.0",
    "zustand": "^4.5.0",
    "react-i18next": "^14.0.0",
    "i18next": "^23.0.0",
    "i18next-browser-languagedetector": "^7.2.0",
    "axios": "^1.6.0",
    "date-fns": "^3.0.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.0.0",
    "lucide-react": "^0.400.0",
    "@radix-ui/react-dialog": "^1.0.0",
    "@radix-ui/react-dropdown-menu": "^2.0.0",
    "@radix-ui/react-slider": "^1.1.0",
    "@radix-ui/react-switch": "^1.0.0",
    "@radix-ui/react-tooltip": "^1.0.0",
    "@radix-ui/react-select": "^2.0.0",
    "@radix-ui/react-tabs": "^1.0.0",
    "@radix-ui/react-progress": "^1.0.0",
    "@radix-ui/react-separator": "^1.0.0",
    "@radix-ui/react-avatar": "^1.0.0",
    "@radix-ui/react-badge": "^1.0.0",
    "class-variance-authority": "^0.7.0",
    "@tauri-apps/api": "^2.0.0",
    "@tauri-apps/plugin-shell": "^2.0.0",
    "@tauri-apps/plugin-notification": "^2.0.0",
    "@tauri-apps/plugin-fs": "^2.0.0",
    "@tauri-apps/plugin-dialog": "^2.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "@tauri-apps/cli": "^2.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "eslint": "^8.57.0",
    "@typescript-eslint/eslint-plugin": "^7.0.0",
    "@typescript-eslint/parser": "^7.0.0"
  }
}
```

### 1.2 Backend — requirements.txt

```
# Web framework
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.0
pydantic-settings==2.2.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9

# Database
sqlalchemy==2.0.30
geoalchemy2==0.15.0
psycopg2-binary==2.9.9
alembic==1.13.0
pysqlite3-binary==0.5.2

# Data pipeline orchestration
prefect==2.19.0
prefect-sqlalchemy==0.4.0

# Custom import UI
mage-ai==0.9.72

# Geospatial processing
rasterio==1.3.10
fiona==1.9.6
shapely==2.0.4
pyproj==3.6.1
geopandas==0.14.4
gdal==3.8.4
numpy==1.26.4
scipy==1.13.0
pyshp==2.3.1

# Machine learning
scikit-learn==1.5.0
prophet==1.1.5
mlflow==2.13.0
joblib==1.4.2
pandas==2.2.2
pyecharts==2.0.4

# Report generation
weasyprint==62.0
jinja2==3.1.4
playwright==1.44.0

# HTTP clients
httpx==0.27.0
aiohttp==3.9.5
requests==2.32.0
tenacity==8.3.0

# Data source specific
cdsapi==0.7.0
earthengine-api==0.1.400
sentinelhub==3.10.0
pymodis==2.2.0
pyproj==3.6.1

# Data formats
openpyxl==3.1.2
netCDF4==1.7.1
h5py==3.11.0
xmltodict==0.13.0

# Utilities
python-dotenv==1.0.1
structlog==24.1.0
schedule==1.2.1
click==8.1.7
rich==13.7.1
apscheduler==3.10.4
```

### 1.3 Desktop Shell — Cargo.toml

```toml
[package]
name = "raphael"
version = "1.0.0"
edition = "2021"

[lib]
name = "raphael_lib"
crate-type = ["staticlib", "cdylib"]

[dependencies]
tauri = { version = "2.0.0", features = ["tray-icon", "image-png"] }
tauri-plugin-shell = "2.0.0"
tauri-plugin-notification = "2.0.0"
tauri-plugin-fs = "2.0.0"
tauri-plugin-http = "2.0.0"
tauri-plugin-dialog = "2.0.0"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tokio = { version = "1.0", features = ["full"] }
reqwest = { version = "0.12", features = ["json"] }
log = "0.4"
env_logger = "0.11"

[build-dependencies]
tauri-build = { version = "2.0.0", features = [] }
```

---

## 2. Configuration Files

### 2.1 app.toml

```toml
[application]
name = "Raphael"
version = "1.0.0"
data_dir = "${APP_DATA}/raphael"
log_level = "info"
demo_mode_available = true

[database]
auto_select = true
ram_threshold_gb = 6
spatialite_path = "${DATA_DIR}/raphael.db"
postgres_port = 5433
postgres_data_dir = "${DATA_DIR}/postgres"
retention_days_observations = 730
retention_days_raster = 90
retention_days_ml_outputs = 365

[api]
host = "127.0.0.1"
port = 8000
workers = 2

[mlflow]
host = "127.0.0.1"
port = 5000
artifact_root = "${DATA_DIR}/mlflow"

[prefect]
host = "127.0.0.1"
port = 4200

[mage]
host = "127.0.0.1"
port = 6789
project_dir = "${DATA_DIR}/mage"

[sync]
default_interval_hours = 6
retry_attempts = 3
retry_delay_seconds = 60
timeout_seconds = 30
offline_retry_interval_minutes = 30

[tiles]
storage_dir = "${DATA_DIR}/tiles"
default_max_zoom = 14
city_max_zoom = 16

[reports]
output_dir = "${DATA_DIR}/reports"
max_concurrent_jobs = 2

[ui]
default_language = "en"
default_basemap = "dark"
default_region = null
```

### 2.2 datasources.toml

```toml
# AIR QUALITY SOURCES

[openaq]
enabled = true
base_url = "https://api.openaq.org/v3"
api_key = ""
parameters = ["pm25", "pm10", "no2", "o3", "co", "so2"]
lookback_hours = 24
schedule_hours = 1

[waqi]
enabled = true
base_url = "https://api.waqi.info"
api_key = "${WAQI_API_KEY}"
schedule_hours = 1

[iqair]
enabled = true
base_url = "https://api.airvisual.com/v2"
api_key = "${IQAIR_API_KEY}"
schedule_hours = 1

[copernicus_cams]
enabled = false
base_url = "https://ads.atmosphere.copernicus.eu/api/v2"
api_key = "${CAMS_API_KEY}"
variables = ["pm2p5", "pm10", "no2", "o3", "co"]
schedule_hours = 6

# WEATHER SOURCES

[open_meteo]
enabled = true
base_url = "https://api.open-meteo.com/v1"
forecast_days = 7
historical_days = 30
variables = [
  "temperature_2m", "precipitation", "wind_speed_10m",
  "wind_direction_10m", "relative_humidity_2m", "uv_index",
  "surface_pressure", "cloud_cover"
]
schedule_hours = 1

[noaa_gfs]
enabled = true
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
variables = ["TMP", "UGRD", "VGRD", "APCP", "RH"]
schedule_hours = 6

[openweathermap]
enabled = true
base_url = "https://api.openweathermap.org/data/2.5"
api_key = "${OWM_API_KEY}"
schedule_hours = 1

[copernicus_era5]
enabled = false
base_url = "https://cds.climate.copernicus.eu/api/v2"
api_key = "${ERA5_API_KEY}"
variables = ["2m_temperature", "total_precipitation", "surface_pressure"]
schedule_hours = 24

# SATELLITE AND FIRE SOURCES

[nasa_firms]
enabled = true
base_url = "https://firms.modaps.eosdis.nasa.gov/api"
map_key = "${NASA_FIRMS_KEY}"
dataset = "VIIRS_SNPP_NRT"
lookback_days = 1
schedule_hours = 3

[nasa_lance]
enabled = true
base_url = "https://lance.modaps.eosdis.nasa.gov"
api_key = "${NASA_EARTHDATA_TOKEN}"
products = ["VNP14IMGTDL_NRT", "MOD14A1"]
schedule_hours = 3

[nasa_earthdata_modis_lst]
enabled = true
base_url = "https://cmr.earthdata.nasa.gov/search"
username = "${EARTHDATA_USERNAME}"
password = "${EARTHDATA_PASSWORD}"
product = "MOD11A1"
schedule_days = 1

[nasa_earthdata_modis_ndvi]
enabled = true
base_url = "https://cmr.earthdata.nasa.gov/search"
username = "${EARTHDATA_USERNAME}"
password = "${EARTHDATA_PASSWORD}"
product = "MOD13A2"
schedule_days = 16

[copernicus_sentinel2]
enabled = false
base_url = "https://services.sentinel-hub.com"
client_id = "${SENTINEL_CLIENT_ID}"
client_secret = "${SENTINEL_CLIENT_SECRET}"
ndvi_formula = "(B08-B04)/(B08+B04)"
schedule_days = 5

[usgs_earth_explorer]
enabled = false
base_url = "https://m2m.cr.usgs.gov/api/api/json/stable"
username = "${USGS_USERNAME}"
password = "${USGS_PASSWORD}"
dataset = "LANDSAT_8_C2_L2"
schedule_days = 16

# VEGETATION SOURCES

[global_forest_watch]
enabled = true
base_url = "https://data-api.globalforestwatch.org"
api_key = "${GFW_API_KEY}"
datasets = ["umd_glad_alerts", "gfw_integrated_alerts"]
schedule_days = 7

[hansen_forest_change]
enabled = true
base_url = "https://storage.googleapis.com/earthenginepartners-hansen"
version = "GFC-2023-v1.11"
schedule_days = 365

# GEOSPATIAL SOURCES

[gadm]
enabled = true
base_url = "https://geodata.ucdavis.edu/gadm"
version = "4.1"
format = "gpkg"
schedule_days = 730

[overpass]
enabled = true
base_url = "https://overpass-api.de/api/interpreter"
features = ["park", "water", "forest", "industrial", "residential"]
schedule_days = 7

[ghsl]
enabled = true
base_url = "https://ghsl.jrc.ec.europa.eu/download.php"
product = "GHS_BUILT_S"
resolution = "100m"
schedule_days = 365

[worldpop]
enabled = false
base_url = "https://hub.worldpop.org/geodata"
resolution = "1km"
schedule_days = 365

[nasa_sedac]
enabled = false
base_url = "https://sedac.ciesin.columbia.edu/data"
datasets = ["gpw-v4-population-density"]
schedule_days = 365

[datameet]
enabled = true
base_url = "https://raw.githubusercontent.com/datameet/maps/master"
datasets = ["Districts", "Assembly_Constituencies", "Municipal_Wards"]
country = "india"
schedule_days = 730

# HAZARD SOURCES

[gdacs]
enabled = true
rss_url = "https://www.gdacs.org/xml/rss.xml"
alert_types = ["FL", "TC", "EQ", "VO", "DR"]
schedule_hours = 1

[fema_flood]
enabled = false
base_url = "https://hazards.fema.gov/gis/nfhl/rest/services"
schedule_days = 30

[emdat]
enabled = false
base_url = "https://public.emdat.be/api"
api_key = "${EMDAT_API_KEY}"
schedule_days = 7

[noaa_ncei]
enabled = true
base_url = "https://www.ncei.noaa.gov/access/services/data/v1"
dataset = "global-summary-of-the-day"
schedule_days = 7
```

### 2.3 ml.toml

```toml
[forecast.prophet]
changepoint_prior_scale = 0.05
seasonality_prior_scale = 10.0
seasonality_mode = "multiplicative"
yearly_seasonality = true
weekly_seasonality = true
daily_seasonality = true
uncertainty_samples = 1000
forecast_horizon_hours = 48

[anomaly.isolation_forest]
n_estimators = 100
contamination = 0.05
max_samples = "auto"
random_state = 42
rolling_window_days = 7

[clustering.kmeans]
n_clusters = 5
init = "k-means++"
n_init = 10
max_iter = 300
random_state = 42
refit_interval_days = 7

[risk_score]
weight_aqi = 0.40
weight_lst = 0.35
weight_ndvi = 0.25
normalization = "minmax"
score_range = [0, 100]
high_risk_threshold = 70
critical_risk_threshold = 85

[retraining]
min_observations_forecast = 30
min_observations_anomaly = 14
retrain_after_n_new_obs = 10
nightly_retrain_hour = 2
```

---

## 3. Environment Variables

```bash
# .env  (never committed to version control)

# NASA
EARTHDATA_USERNAME=your_nasa_earthdata_username
EARTHDATA_PASSWORD=your_nasa_earthdata_password
EARTHDATA_TOKEN=your_nasa_earthdata_bearer_token
NASA_FIRMS_KEY=your_nasa_firms_map_key

# ESA / Copernicus
SENTINEL_CLIENT_ID=your_sentinel_hub_client_id
SENTINEL_CLIENT_SECRET=your_sentinel_hub_client_secret
CAMS_API_KEY=your_copernicus_cams_key
ERA5_API_KEY=your_copernicus_cds_key

# Air Quality
WAQI_API_KEY=your_waqi_token
IQAIR_API_KEY=your_iqair_key
OWM_API_KEY=your_openweathermap_key

# Vegetation
GFW_API_KEY=your_global_forest_watch_key

# Hazard
EMDAT_API_KEY=your_emdat_key

# USGS
USGS_USERNAME=your_usgs_username
USGS_PASSWORD=your_usgs_password

# Application
RAPHAEL_ENV=production
RAPHAEL_SECRET_KEY=generate_with_openssl_rand_hex_32
RAPHAEL_DATA_DIR=/path/to/data

# Database (PostGIS mode only)
POSTGRES_USER=raphael
POSTGRES_PASSWORD=strong_password_here
POSTGRES_DB=raphael_db
```

---

## 4. Database Schema — Full Migration

```sql
-- migrations/versions/001_initial_schema.sql

CREATE EXTENSION IF NOT EXISTS postgis;
-- SpatiaLite equivalent: SELECT InitSpatialMetaData();

-- USERS AND AUTH

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(100) UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    display_name    VARCHAR(200),
    role            VARCHAR(20) NOT NULL DEFAULT 'viewer'
                    CHECK (role IN ('admin', 'analyst', 'field_worker', 'viewer')),
    organization    VARCHAR(200),
    preferred_language CHAR(5) DEFAULT 'en',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_active_at  TIMESTAMPTZ
);

CREATE TABLE activity_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(50),
    resource_id     UUID,
    metadata        JSONB,
    performed_at    TIMESTAMPTZ DEFAULT NOW()
);

-- REGIONS AND SOURCES

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

CREATE INDEX idx_regions_bbox ON regions USING GIST(bbox);

CREATE TABLE sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key             VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,
    category        VARCHAR(50) NOT NULL,
    layer_types     TEXT[] NOT NULL,
    base_url        TEXT,
    is_enabled      BOOLEAN DEFAULT true,
    last_synced_at  TIMESTAMPTZ,
    last_error      TEXT,
    error_count     INT DEFAULT 0
);

-- ENVIRONMENTAL OBSERVATIONS

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

CREATE INDEX idx_raw_obs_layer_region   ON raw_observations(layer_type, region_id);
CREATE INDEX idx_raw_obs_observed_at    ON raw_observations(observed_at DESC);
CREATE INDEX idx_raw_obs_geometry       ON raw_observations USING GIST(geometry);
CREATE INDEX idx_raw_obs_station        ON raw_observations(station_id);
CREATE INDEX idx_raw_obs_source         ON raw_observations(source_id);

-- ZONES

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

CREATE INDEX idx_zones_region   ON zone_geometries(region_id);
CREATE INDEX idx_zones_geometry ON zone_geometries USING GIST(geometry);

-- RASTER TILES

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

CREATE INDEX idx_raster_layer_region ON raster_tiles(layer_type, region_id);
CREATE INDEX idx_raster_valid_date   ON raster_tiles(valid_date DESC);

-- ML OUTPUTS

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

CREATE INDEX idx_ml_type        ON ml_outputs(model_type, output_type);
CREATE INDEX idx_ml_zone        ON ml_outputs(zone_id);
CREATE INDEX idx_ml_valid       ON ml_outputs(valid_from, valid_to);
CREATE INDEX idx_ml_computed    ON ml_outputs(computed_at DESC);

-- ALERTS

CREATE TABLE alert_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    name            VARCHAR(200) NOT NULL,
    layer_type      VARCHAR(50) NOT NULL,
    geometry        geometry(Geometry, 4326),
    zone_id         UUID REFERENCES zone_geometries(id),
    operator        VARCHAR(20) NOT NULL
                    CHECK (operator IN ('gt', 'lt', 'change_gt', 'change_lt')),
    threshold       FLOAT NOT NULL,
    severity        VARCHAR(20) NOT NULL DEFAULT 'warning'
                    CHECK (severity IN ('info', 'warning', 'critical')),
    time_window     JSONB,
    radius_km       FLOAT,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

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

CREATE INDEX idx_alert_events_rule      ON alert_events(rule_id);
CREATE INDEX idx_alert_events_triggered ON alert_events(triggered_at DESC);

-- CUSTOM IMPORTS

CREATE TABLE import_datasets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    name            VARCHAR(200) NOT NULL,
    format          VARCHAR(20) NOT NULL
                    CHECK (format IN ('csv', 'geojson', 'kml', 'shapefile', 'excel')),
    row_count       INT,
    schema_map      JSONB NOT NULL,
    layer_type      VARCHAR(50),
    mage_pipeline_id VARCHAR(100),
    imported_at     TIMESTAMPTZ DEFAULT NOW(),
    is_visible      BOOLEAN DEFAULT true
);

-- EVENT MARKERS

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

-- SEED DATA

INSERT INTO users (username, password_hash, display_name, role)
VALUES (
    'admin',
    '$2b$12$PLACEHOLDER_HASH_CHANGE_ON_FIRST_RUN',
    'Administrator',
    'admin'
);

INSERT INTO sources (key, name, category, layer_types) VALUES
('openaq',          'OpenAQ v3',                    'air_quality',  ARRAY['aq']),
('waqi',            'World AQI',                    'air_quality',  ARRAY['aq']),
('iqair',           'IQAir AirVisual',              'air_quality',  ARRAY['aq']),
('copernicus_cams', 'Copernicus CAMS',              'air_quality',  ARRAY['aq']),
('open_meteo',      'Open-Meteo',                   'weather',      ARRAY['weather', 'precipitation']),
('noaa_gfs',        'NOAA GFS',                     'weather',      ARRAY['weather']),
('openweathermap',  'OpenWeatherMap',               'weather',      ARRAY['weather']),
('copernicus_era5', 'ERA5 Reanalysis',              'climate',      ARRAY['climate']),
('nasa_firms',      'NASA FIRMS VIIRS',             'fire',         ARRAY['fire']),
('nasa_lance',      'NASA LANCE NRT',               'fire',         ARRAY['fire']),
('modis_lst',       'NASA MODIS LST',               'satellite',    ARRAY['lst']),
('modis_ndvi',      'NASA MODIS NDVI',              'satellite',    ARRAY['ndvi']),
('sentinel2',       'Copernicus Sentinel-2',        'satellite',    ARRAY['ndvi']),
('usgs_landsat',    'USGS Earth Explorer Landsat',  'satellite',    ARRAY['ndvi', 'lst']),
('gfw',             'Global Forest Watch',          'vegetation',   ARRAY['ndvi']),
('hansen',          'Hansen Forest Change',         'vegetation',   ARRAY['ndvi']),
('gadm',            'GADM Boundaries',              'geospatial',   ARRAY['boundaries']),
('overpass',        'OpenStreetMap Overpass',       'geospatial',   ARRAY['urban']),
('ghsl',            'GHSL Built-up Layer',          'geospatial',   ARRAY['urban']),
('worldpop',        'WorldPop Density',             'geospatial',   ARRAY['population']),
('nasa_sedac',      'NASA SEDAC',                   'geospatial',   ARRAY['socioeconomic']),
('datameet',        'Datameet India',               'geospatial',   ARRAY['boundaries']),
('gdacs',           'GDACS Disaster Alerts',        'hazard',       ARRAY['hazard']),
('fema_flood',      'FEMA Flood Zones',             'hazard',       ARRAY['hazard']),
('emdat',           'EM-DAT Disaster DB',           'hazard',       ARRAY['hazard']),
('noaa_ncei',       'NOAA NCEI Events',             'hazard',       ARRAY['hazard']);
```

---

## 5. API Contracts

### 5.1 Layer Current Data

```
GET /api/v1/layers/{layer_type}/current
    ?region_id={uuid}
    &bbox={west},{south},{east},{north}
    &source={openaq|waqi|iqair}    (optional filter)

layer_type options: aq | lst | ndvi | fire | precipitation |
                    urban | risk | stations | boundaries

Response 200:
{
  "status": "success",
  "data": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": { "type": "Point", "coordinates": [77.2090, 28.6139] },
        "properties": {
          "station_id": "IN-DEL-001",
          "station_name": "Anand Vihar",
          "value": 178.4,
          "unit": "ug/m3",
          "aqi": 178,
          "aqi_category": "Very Poor",
          "observed_at": "2025-05-18T14:00:00Z",
          "source": "openaq",
          "is_anomalous": false,
          "anomaly_score": 0.12
        }
      }
    ]
  },
  "meta": {
    "layer_type": "aq",
    "count": 24,
    "last_synced": "2025-05-18T12:00:00Z",
    "sources_active": ["openaq", "waqi", "iqair"],
    "coverage_pct": 78
  }
}
```

### 5.2 Forecast

```
GET /api/v1/layers/{layer_type}/forecast
    ?zone_id={uuid}&hours=48

Response 200:
{
  "status": "success",
  "data": {
    "zone_id": "uuid",
    "layer_type": "aq",
    "model_version": "prophet-1.2.3",
    "mlflow_run_id": "abc123def456",
    "training_observations": 2184,
    "forecast": [
      {
        "timestamp": "2025-05-18T15:00:00Z",
        "value": 182.1,
        "lower_bound": 162.4,
        "upper_bound": 201.8,
        "is_exceedance": false
      }
    ],
    "exceedance_windows": [
      {
        "from": "2025-05-19T02:00:00Z",
        "to": "2025-05-19T08:00:00Z",
        "peak_value": 224.1,
        "probability": 0.73,
        "threshold": 200.0
      }
    ],
    "explanation": "PM2.5 forecast to rise overnight. Wind speed drops below 5 km/h from 11 PM. Temperature inversion expected. Peak between 2 AM and 8 AM."
  },
  "meta": {
    "confidence_level": 0.80,
    "computed_at": "2025-05-18T12:00:00Z"
  }
}
```

### 5.3 Zone Scorecard

```
GET /api/v1/zones/{id}/scorecard

Response 200:
{
  "status": "success",
  "data": {
    "zone": {
      "id": "uuid",
      "name": "Anand Vihar",
      "admin_level": 3,
      "region": "Delhi NCT"
    },
    "indicators": {
      "aq":   { "current": 178.4, "unit": "ug/m3",  "category": "Very Poor", "trend_30d": "worsening", "trend_pct": 12.4 },
      "lst":  { "current": 44.2,  "unit": "celsius", "category": "High",      "trend_30d": "stable",    "trend_pct": 1.2  },
      "ndvi": { "current": 0.12,  "unit": "index",   "category": "Very Low",  "trend_30d": "stable",    "trend_pct": -0.8 },
      "fire": { "current": 2,     "unit": "count",   "category": "Elevated",  "trend_30d": "improving", "trend_pct": -40  },
      "precip": { "current": 0.0, "unit": "mm",      "category": "None",      "trend_30d": "stable",    "trend_pct": 0    }
    },
    "risk_score": {
      "value": 78,
      "category": "High Risk",
      "explanation": "Risk elevated due to very poor air quality, high land surface temperature, and critically low green cover.",
      "contributions": { "aq": 34.2, "lst": 26.4, "ndvi": 17.4 }
    },
    "data_sources": ["openaq", "waqi", "modis_lst", "modis_ndvi"],
    "recent_alerts": [
      {
        "id": "uuid",
        "rule_name": "PM2.5 Warning",
        "triggered_at": "2025-05-18T09:00:00Z",
        "severity": "warning",
        "value": 178.4
      }
    ],
    "event_markers": []
  }
}
```

### 5.4 Report Generation

```
POST /api/v1/reports/generate
Content-Type: application/json

{
  "report_type": "zone",
  "title": "Environmental Assessment — Anand Vihar",
  "organization": "Delhi Green NGO",
  "date_range": { "from": "2025-04-18", "to": "2025-05-18" },
  "zones": ["uuid1"],
  "sections": ["map_snapshot", "scorecard", "trend_charts",
               "risk_score", "alert_log", "narrative"],
  "layers_active": ["aq", "lst", "ndvi", "risk"],
  "language": "en"
}

Response 202:
{
  "status": "success",
  "data": {
    "job_id": "uuid",
    "estimated_seconds": 45
  }
}

GET /api/v1/reports/{job_id}/status
Response 200:
{
  "status": "success",
  "data": {
    "job_id": "uuid",
    "state": "completed",
    "progress_pct": 100,
    "file_size_bytes": 2847291,
    "created_at": "2025-05-18T14:30:00Z"
  }
}

GET /api/v1/reports/{job_id}/download
Response: application/pdf binary
```

---

## 6. ML Implementation

### 6.1 Prophet Forecast Wrapper

```python
# backend/ml/forecast.py

from prophet import Prophet
import pandas as pd
import mlflow
from ..db.queries import get_observations_for_zone
from ..config import ML_CONFIG

def train_and_forecast(zone_id: str, layer_type: str, horizon_hours: int = 48) -> dict:
    obs = get_observations_for_zone(zone_id, layer_type, lookback_days=90)
    if len(obs) < ML_CONFIG["retraining"]["min_observations_forecast"]:
        return {"error": "insufficient_data", "count": len(obs)}

    df = pd.DataFrame(obs, columns=["ds", "y"])
    df["ds"] = pd.to_datetime(df["ds"])

    cfg = ML_CONFIG["forecast"]["prophet"]
    m = Prophet(
        changepoint_prior_scale=cfg["changepoint_prior_scale"],
        seasonality_prior_scale=cfg["seasonality_prior_scale"],
        seasonality_mode=cfg["seasonality_mode"],
        uncertainty_samples=cfg["uncertainty_samples"]
    )
    m.add_seasonality(name="daily", period=1, fourier_order=8)

    experiment_name = f"{layer_type}_forecast_{zone_id[:8]}"
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run():
        mlflow.log_params({
            "zone_id": zone_id,
            "layer_type": layer_type,
            "training_rows": len(df),
            "horizon_hours": horizon_hours
        })
        m.fit(df)
        future = m.make_future_dataframe(periods=horizon_hours, freq="h")
        forecast = m.predict(future)
        tail = forecast.tail(horizon_hours)
        mlflow.log_metric("forecast_mean", float(tail["yhat"].mean()))
        mlflow.log_metric("forecast_range", float(tail["yhat"].max() - tail["yhat"].min()))

    return {
        "forecast": tail[["ds", "yhat", "yhat_lower", "yhat_upper"]].to_dict("records"),
        "training_rows": len(df)
    }
```

### 6.2 IsolationForest Anomaly Detection

```python
# backend/ml/anomaly.py

