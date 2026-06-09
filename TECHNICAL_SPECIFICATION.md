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
