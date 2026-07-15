import sys
import os

# Ensure the backend directory is in python search path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

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
