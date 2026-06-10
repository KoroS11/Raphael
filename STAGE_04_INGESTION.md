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
