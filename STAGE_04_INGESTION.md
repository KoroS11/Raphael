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
