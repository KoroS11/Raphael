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
