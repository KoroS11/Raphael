# Stage 04 — Data Ingestion Pipeline (Prefect)

## Prerequisites
Stage 03 completed. FastAPI running and returning 200 on /health.

## Objective
Build all 24 Prefect data ingestion flows. Each flow pulls from one open data source, validates and normalizes the data, and writes it to the database. By the end of this stage, running a sync will populate the database with real environmental data that the map layers in Stage 07 will visualize.

Reference: Every source in this stage feeds a specific map layer visible in the Raphael dashboard mockup — the heatmaps, 3D AQ columns, fire dots, NDVI overlay, and admin boundaries all originate from these flows.

---

## Step 1 — Install and Configure Prefect

With backend venv active:

```
prefect server start --host 127.0.0.1 --port 4200
```

Open a second terminal and set the API URL:
```
prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api
```

Verify Prefect UI is accessible at http://localhost:4200

---

## Step 2 — Create the Base Flow Class

Create `backend/ingestion/base.py`:

```python
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from db.models import Source, RawObservation, Region
from datetime import datetime, timezone
from typing import Optional
import uuid

log = structlog.get_logger()

class BaseIngestionFlow:
    source_key: str = ""
    layer_type: str = ""

    def __init__(self):
        self.db: Session = SessionLocal()
        self.source = self.db.query(Source).filter(Source.key == self.source_key).first()
        self.region = self.db.query(Region).filter(Region.is_active == True).first()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60))
    def fetch(self, url: str, params: dict = None, headers: dict = None) -> dict:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(url, params=params, headers=headers)
            r.raise_for_status()
            return r.json()

    def is_online(self) -> bool:
        try:
            httpx.get("https://dns.google", timeout=5)
            return True
        except Exception:
            return False

    def bulk_write(self, observations: list[dict]):
        if not observations:
            return
        rows = [RawObservation(**obs) for obs in observations]
        self.db.bulk_save_objects(rows)
        self.db.commit()
        log.info("wrote_observations", count=len(rows), source=self.source_key)

    def update_source_sync_time(self):
        if self.source:
            self.source.last_synced_at = datetime.now(timezone.utc)
            self.source.error_count = 0
            self.db.commit()

    def record_error(self, error: str):
        if self.source:
            self.source.last_error = str(error)
            self.source.error_count += 1
            self.db.commit()

    def normalize_point(self, lat: float, lon: float) -> str:
        return f"SRID=4326;POINT({lon} {lat})"

    def close(self):
        self.db.close()
```

---

## Step 3 — Implement Air Quality Flows

### Flow 1 — OpenAQ (Primary AQ Source)

Create `backend/ingestion/flows/aq_openaq.py`:

```python
from prefect import flow, task
import os, uuid
from datetime import datetime, timezone
from ingestion.base import BaseIngestionFlow

BASE_URL = "https://api.openaq.org/v3"
API_KEY  = os.getenv("OPENAQ_API_KEY", "")

class OpenAQFlow(BaseIngestionFlow):
    source_key = "openaq"
    layer_type  = "aq"

@task(name="fetch-openaq-locations", retries=3)
def fetch_locations(bbox: tuple) -> list:
    flow_obj = OpenAQFlow()
    if not flow_obj.is_online():
        return []
    west, south, east, north = bbox
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    data = flow_obj.fetch(
        f"{BASE_URL}/locations",
        params={
            "bbox":       f"{west},{south},{east},{north}",
            "limit":      1000,
            "parameters": "pm25,pm10,no2,o3,co"
        },
        headers=headers
    )
    return data.get("results", [])

@task(name="fetch-openaq-measurements", retries=3)
def fetch_measurements(location_id: int) -> list:
    flow_obj = OpenAQFlow()
    headers  = {"X-API-Key": API_KEY} if API_KEY else {}
    data = flow_obj.fetch(
        f"{BASE_URL}/measurements",
        params={"location_id": location_id, "parameter": "pm25", "limit": 24},
        headers=headers
    )
    return data.get("results", [])

@task(name="write-openaq-to-db")
def write_to_db(locations: list, flow_obj: OpenAQFlow):
    observations = []
    for loc in locations:
        for sensor in loc.get("sensors", []):
            latest = sensor.get("latest", {})
            if not latest.get("value"):
                continue
            observations.append({
                "id":           uuid.uuid4(),
                "source_id":    flow_obj.source.id,
                "region_id":    flow_obj.region.id,
                "layer_type":   "aq",
                "geometry":     flow_obj.normalize_point(
                                    loc["coordinates"]["latitude"],
                                    loc["coordinates"]["longitude"]
                                ),
                "value":        float(latest["value"]),
                "unit":         "ug/m3",
                "station_id":   str(loc["id"]),
                "station_name": loc.get("name", ""),
                "observed_at":  datetime.fromisoformat(
                                    latest["datetime"].replace("Z", "+00:00")
                                ) if latest.get("datetime") else datetime.now(timezone.utc),
                "raw_payload":  latest
            })
    flow_obj.bulk_write(observations)
    flow_obj.update_source_sync_time()
    return len(observations)

@flow(name="openaq-ingestion", log_prints=True)
def openaq_flow():
    flow_obj = OpenAQFlow()
    if not flow_obj.region:
        print("No active region configured. Skipping.")
        return

    bbox = flow_obj.db.execute(
        "SELECT ST_XMin(bbox), ST_YMin(bbox), ST_XMax(bbox), ST_YMax(bbox) FROM regions WHERE is_active = true"
    ).fetchone()

    locations = fetch_locations(tuple(bbox))
    print(f"Found {len(locations)} OpenAQ stations")
    count = write_to_db(locations, flow_obj)
    print(f"Wrote {count} observations")
    flow_obj.close()

if __name__ == "__main__":
    openaq_flow()
```

### Flow 2 — WAQI

Create `backend/ingestion/flows/aq_waqi.py`:

```python
from prefect import flow, task
import os, uuid
from datetime import datetime, timezone
from ingestion.base import BaseIngestionFlow

BASE_URL = "https://api.waqi.info"
API_KEY  = os.getenv("WAQI_API_KEY", "")

class WAQIFlow(BaseIngestionFlow):
    source_key = "waqi"
    layer_type  = "aq"

@task(name="fetch-waqi-stations", retries=3)
def fetch_waqi_stations(bbox: tuple) -> list:
    if not API_KEY:
        return []
    flow_obj = WAQIFlow()
    south, west, north, east = bbox[1], bbox[0], bbox[3], bbox[2]
    data = flow_obj.fetch(
        f"{BASE_URL}/map/bounds/",
        params={"latlng": f"{south},{west},{north},{east}", "token": API_KEY}
    )
    return data.get("data", [])

@task(name="write-waqi-to-db")
def write_waqi_to_db(stations: list):
    flow_obj = WAQIFlow()
    observations = []
    for station in stations:
        if station.get("aqi") == "-":
            continue
        try:
            aqi = float(station["aqi"])
        except (ValueError, TypeError):
            continue
        observations.append({
            "id":           uuid.uuid4(),
            "source_id":    flow_obj.source.id,
            "region_id":    flow_obj.region.id,
            "layer_type":   "aq",
            "geometry":     flow_obj.normalize_point(station["lat"], station["lon"]),
            "value":        aqi,
            "unit":         "AQI",
            "station_id":   str(station["uid"]),
            "station_name": station.get("station", {}).get("name", ""),
            "observed_at":  datetime.now(timezone.utc),
            "raw_payload":  station
        })
    flow_obj.bulk_write(observations)
    flow_obj.update_source_sync_time()
    flow_obj.close()

@flow(name="waqi-ingestion")
def waqi_flow():
    flow_obj = WAQIFlow()
    bbox = (76.8, 28.4, 77.4, 28.9)  # Loaded from active region in production
    stations = fetch_waqi_stations(bbox)
    print(f"Fetched {len(stations)} WAQI stations")
    write_waqi_to_db(stations)
    flow_obj.close()
```

### Flow 3 — IQAir

Create `backend/ingestion/flows/aq_iqair.py`:

```python
from prefect import flow, task
import os, uuid
from datetime import datetime, timezone
from ingestion.base import BaseIngestionFlow

BASE_URL = "https://api.airvisual.com/v2"
API_KEY  = os.getenv("IQAIR_API_KEY", "")

class IQAirFlow(BaseIngestionFlow):
    source_key = "iqair"
    layer_type  = "aq"

@task(name="fetch-iqair-nearest", retries=3)
def fetch_iqair(lat: float, lon: float) -> dict:
    if not API_KEY:
        return {}
    flow_obj = IQAirFlow()
    return flow_obj.fetch(
        f"{BASE_URL}/nearest_city",
        params={"lat": lat, "lon": lon, "key": API_KEY}
    )

@task(name="write-iqair-to-db")
def write_iqair(data: dict):
    flow_obj = IQAirFlow()
    d = data.get("data", {})
    pollution = d.get("current", {}).get("pollution", {})
    location  = d.get("location", {}).get("coordinates", [None, None])
    if not pollution or not location[0]:
        return
    flow_obj.bulk_write([{
        "id":           uuid.uuid4(),
        "source_id":    flow_obj.source.id,
        "region_id":    flow_obj.region.id,
        "layer_type":   "aq",
        "geometry":     flow_obj.normalize_point(location[1], location[0]),
        "value":        float(pollution.get("aqius", 0)),
        "unit":         "AQI (US)",
        "station_name": d.get("city", ""),
        "observed_at":  datetime.now(timezone.utc),
        "raw_payload":  pollution
    }])
    flow_obj.update_source_sync_time()
    flow_obj.close()

@flow(name="iqair-ingestion")
def iqair_flow():
    # Query centroid of active region
    lat, lon = 28.6139, 77.2090
    data = fetch_iqair(lat, lon)
    write_iqair(data)
```

---

## Step 4 — Implement Weather Flows

### Flow 4 — Open-Meteo (Primary Weather Source)

Create `backend/ingestion/flows/weather_openmeteo.py`:

```python
from prefect import flow, task
import uuid
from datetime import datetime, timezone
from ingestion.base import BaseIngestionFlow

BASE_URL = "https://api.open-meteo.com/v1"

VARIABLES = [
    "temperature_2m", "precipitation", "wind_speed_10m",
    "wind_direction_10m", "relative_humidity_2m",
    "uv_index", "surface_pressure", "cloud_cover"
]

class OpenMeteoFlow(BaseIngestionFlow):
    source_key = "open_meteo"
    layer_type  = "weather"

@task(name="fetch-open-meteo", retries=3)
def fetch_weather(lat: float, lon: float) -> dict:
    flow_obj = OpenMeteoFlow()
    return flow_obj.fetch(
        f"{BASE_URL}/forecast",
        params={
            "latitude":      lat,
            "longitude":     lon,
            "hourly":        ",".join(VARIABLES),
            "forecast_days": 7,
            "timezone":      "auto"
        }
    )

@task(name="write-weather-to-db")
def write_weather(data: dict, lat: float, lon: float):
    flow_obj = OpenMeteoFlow()
    hourly   = data.get("hourly", {})
    times    = hourly.get("time", [])

    observations = []
    for i, t in enumerate(times[:24]):  # Store next 24h
        for var in VARIABLES:
            val = hourly.get(var, [])[i] if i < len(hourly.get(var, [])) else None
            if val is None:
                continue
            observations.append({
                "id":           uuid.uuid4(),
                "source_id":    flow_obj.source.id,
                "region_id":    flow_obj.region.id,
                "layer_type":   "weather",
                "geometry":     flow_obj.normalize_point(lat, lon),
                "value":        float(val),
                "unit":         _unit(var),
                "station_id":   f"openmeteo_{var}",
                "station_name": var,
                "observed_at":  datetime.fromisoformat(t),
                "raw_payload":  {"variable": var, "value": val}
            })

    flow_obj.bulk_write(observations)
    flow_obj.update_source_sync_time()
    flow_obj.close()
    return len(observations)

def _unit(var: str) -> str:
    units = {
        "temperature_2m": "celsius", "precipitation": "mm",
        "wind_speed_10m": "km/h",    "wind_direction_10m": "degrees",
        "relative_humidity_2m": "%", "uv_index": "index",
        "surface_pressure": "hPa",   "cloud_cover": "%"
    }
    return units.get(var, "")

@flow(name="openmeteo-ingestion")
def openmeteo_flow():
    lat, lon = 28.6139, 77.2090
    data  = fetch_weather(lat, lon)
    count = write_weather(data, lat, lon)
    print(f"Wrote {count} weather observations")
```

---

## Step 5 — Implement Fire Flows

### Flow 5 — NASA FIRMS (Primary Fire Source)

Create `backend/ingestion/flows/fire_firms.py`:

```python
from prefect import flow, task
import os, uuid, csv, io
from datetime import datetime, timezone
from ingestion.base import BaseIngestionFlow

BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api"
MAP_KEY  = os.getenv("NASA_FIRMS_KEY", "")

class FIRMSFlow(BaseIngestionFlow):
    source_key = "nasa_firms"
    layer_type  = "fire"

@task(name="fetch-firms-fires", retries=3)
def fetch_fires(bbox: tuple) -> list:
    if not MAP_KEY:
        print("No NASA FIRMS key configured. Skipping.")
        return []
    flow_obj = FIRMSFlow()
    west, south, east, north = bbox
    bbox_str = f"{west},{south},{east},{north}"
    url = f"{BASE_URL}/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/{bbox_str}/1"
    response = flow_obj.fetch(url)
    # FIRMS returns CSV, not JSON
    import httpx
    r = httpx.get(url, timeout=30)
    reader = csv.DictReader(io.StringIO(r.text))
    return list(reader)

@task(name="write-firms-to-db")
def write_firms(fires: list):
    if not fires:
        return
    flow_obj = FIRMSFlow()
    observations = []
    for fire in fires:
        try:
            lat = float(fire.get("latitude",  0))
            lon = float(fire.get("longitude", 0))
            frp = float(fire.get("frp",       0))
        except (ValueError, TypeError):
            continue

        observations.append({
            "id":           uuid.uuid4(),
            "source_id":    flow_obj.source.id,
            "region_id":    flow_obj.region.id,
            "layer_type":   "fire",
            "geometry":     flow_obj.normalize_point(lat, lon),
            "value":        frp,
            "unit":         "MW",
            "station_name": f"FIRMS_{fire.get('confidence','')}_conf",
            "observed_at":  datetime.now(timezone.utc),
            "raw_payload":  dict(fire)
        })

    flow_obj.bulk_write(observations)
    flow_obj.update_source_sync_time()
    flow_obj.close()
    print(f"Wrote {len(observations)} fire detections")

@flow(name="firms-ingestion")
def firms_flow():
    bbox = (76.8, 28.4, 77.4, 28.9)
    fires = fetch_fires(bbox)
    print(f"Fetched {len(fires)} FIRMS detections")
    write_firms(fires)
```

---

## Step 6 — Implement Satellite Imagery Flow (LST)

Create `backend/ingestion/flows/lst_modis.py`:

```python
from prefect import flow, task
import os, uuid, tempfile
from datetime import date, datetime, timezone
from ingestion.base import BaseIngestionFlow

class MODISLSTFlow(BaseIngestionFlow):
    source_key = "modis_lst"
    layer_type  = "lst"

@task(name="search-modis-granules", retries=2)
def search_granules(bbox: tuple, target_date: date) -> list:
    import httpx
    username = os.getenv("EARTHDATA_USERNAME", "")
    password = os.getenv("EARTHDATA_PASSWORD", "")
    if not username:
        return []

    west, south, east, north = bbox
    r = httpx.get(
        "https://cmr.earthdata.nasa.gov/search/granules.json",
        params={
            "short_name":     "MOD11A1",
            "version":        "061",
            "temporal":       f"{target_date},{target_date}",
            "bounding_box":   f"{west},{south},{east},{north}",
            "page_size":      5
        },
        auth=(username, password),
        timeout=30
    )
    return r.json().get("feed", {}).get("entry", [])

@task(name="download-and-process-lst", retries=1)
def process_lst_granule(granule: dict, bbox: tuple) -> str:
    # Download HDF4, process with Rasterio, return PNG tile path
    # Full Rasterio pipeline is implemented in Stage 05
    # This task is a stub that will be completed in Stage 05
    return ""

@task(name="write-lst-tile-metadata")
def write_tile_metadata(tile_path: str, bbox: tuple, target_date: date):
    if not tile_path:
        return
    from db.connection import SessionLocal
    from db.models import RasterTile, Region
    import uuid
    db = SessionLocal()
    region = db.query(Region).filter(Region.is_active == True).first()
    tile = RasterTile(
        id=uuid.uuid4(),
        layer_type="lst",
        region_id=region.id,
        tile_path=tile_path,
        processed_at=datetime.now(timezone.utc),
        valid_date=target_date,
        resolution_m=1000,
        source="modis_lst"
    )
    db.add(tile)
    db.commit()
    db.close()

@flow(name="modis-lst-ingestion")
def lst_modis_flow():
    bbox        = (76.8, 28.4, 77.4, 28.9)
    target_date = date.today()
    granules    = search_granules(bbox, target_date)
    if not granules:
        print("No MODIS LST granules found for today. Trying yesterday.")
        from datetime import timedelta
