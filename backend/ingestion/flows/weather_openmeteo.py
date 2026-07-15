import sys
import os

# Ensure backend directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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

if __name__ == "__main__":
    openmeteo_flow()
