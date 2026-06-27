import sys
import os
from datetime import datetime, timezone
import asyncio

# Ensure backend directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow, task
import httpx, uuid, xmltodict
from ingestion.base import BaseIngestionFlow
from api.routes.ws import broadcast

GDACS_RSS = "https://www.gdacs.org/xml/rss.xml"

class GDACSFlow(BaseIngestionFlow):
    source_key = "gdacs"
    layer_type  = "hazard"

@task(name="fetch-gdacs-alerts", retries=3)
def fetch_gdacs() -> list:
    flow_obj = GDACSFlow()
    if not flow_obj.is_online():
        print("Offline - skipping fetch")
        asyncio.run(broadcast({
            "type": "trace",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "source": "gdacs",
                "message": "Offline - skipped disaster alert feed fetch"
            }
        }))
        return []

    asyncio.run(broadcast({
        "type": "trace",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "source": "gdacs",
            "message": "Fetching natural disaster indicators from GDACS RSS feed..."
        }
    }))

    try:
        r = httpx.get(GDACS_RSS, timeout=30)
        r.raise_for_status()
        parsed = xmltodict.parse(r.text)
        items  = parsed.get("rss", {}).get("channel", {}).get("item", [])
        results = items if isinstance(items, list) else [items]
        
        asyncio.run(broadcast({
            "type": "trace",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "source": "gdacs",
                "message": f"Successfully parsed {len(results)} active disaster feeds from GDACS"
            }
        }))
        return results
    except Exception as e:
        print("Error fetching GDACS alerts:", e)
        asyncio.run(broadcast({
            "type": "trace",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "source": "gdacs",
                "message": f"Error parsing disaster alerts feed: {str(e)}"
            }
        }))
        return []

def write_gdacs(items: list, flow_obj: GDACSFlow) -> int:
    if not items:
        return 0
        
    observations = []
    
    asyncio.run(broadcast({
        "type": "trace",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "source": "gdacs",
            "message": "Filtering and mapping geographical hazards to database structures..."
        }
    }))

    for item in items:
        try:
            lat = float(item.get("geo:lat", 0))
            lon = float(item.get("geo:long", 0))
            alert_level = item.get("gdacs:alertlevel", "Green")
            severity_map = {"Green": 1.0, "Orange": 2.0, "Red": 3.0}
            value = severity_map.get(alert_level, 1.0)
        except Exception:
            continue

        observations.append({
            "id":           str(uuid.uuid4()),
            "source_id":    flow_obj.source.id,
            "region_id":    flow_obj.region.id,
            "layer_type":   "hazard",
            "geometry":     flow_obj.normalize_point(lat, lon),
            "value":        value,
            "unit":         "severity",
            "station_name": item.get("title", "GDACS Alert"),
            "observed_at":  datetime.now(timezone.utc),
            "raw_payload":  {"title": item.get("title"), "level": alert_level}
        })

    try:
        flow_obj.bulk_write(observations)
        flow_obj.update_source_sync_time()
        
        asyncio.run(broadcast({
            "type": "trace",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "source": "gdacs",
                "message": f"Successfully wrote {len(observations)} disaster hotspot items to DB"
            }
        }))
        return len(observations)
    except Exception as e:
        flow_obj.record_error(str(e))
        asyncio.run(broadcast({
            "type": "trace",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "source": "gdacs",
                "message": f"Error inserting GDACS alerts into DB: {str(e)}"
            }
        }))
        raise e

@flow(name="gdacs-hazard-ingestion")
def gdacs_flow():
    flow_obj = GDACSFlow()
    if not flow_obj.region:
        print("No active region configured. Skipping.")
        return

    items = fetch_gdacs()
    print(f"Fetched {len(items)} GDACS alerts")
    
    count = write_gdacs(items, flow_obj)
    print(f"Wrote {count} hazard observations")

    # Broadcast standard sync status
    asyncio.run(broadcast({
        "type": "sync_status",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "source": "gdacs",
            "layer_type": "hazard",
            "count": count,
            "status": "success"
        }
    }))
    
    flow_obj.close()

if __name__ == "__main__":
    gdacs_flow()
