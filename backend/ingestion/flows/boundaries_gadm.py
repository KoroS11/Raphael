import sys
import os
from datetime import datetime, timezone
import asyncio

# Ensure backend directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow, task
import httpx, uuid
from pathlib import Path
from ingestion.base import BaseIngestionFlow
from api.routes.ws import broadcast

class GADMFlow(BaseIngestionFlow):
    source_key = "gadm"
    layer_type  = "boundaries"

@task(name="download-gadm-boundaries")
def download_gadm(country_iso3: str) -> Path:
    data_dir = Path(os.getenv("RAPHAEL_DATA_DIR", "./data")) / "boundaries"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_file = data_dir / f"gadm41_{country_iso3}.gpkg"

    if out_file.exists():
        print(f"GADM file already exists: {out_file}")
        asyncio.run(broadcast({
            "type": "trace",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "source": "gadm",
                "message": f"Cached GADM boundaries located at {out_file.name}"
            }
        }))
        return out_file

    asyncio.run(broadcast({
        "type": "trace",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "source": "gadm",
            "message": f"Starting download of GADM boundaries GPKG for {country_iso3}"
        }
    }))

    url = f"https://geodata.ucdavis.edu/gadm/gadm4.1/gpkg/gadm41_{country_iso3}.gpkg"
    print(f"Downloading GADM boundaries for {country_iso3}...")
    with httpx.stream("GET", url, timeout=300, follow_redirects=True) as r:
        r.raise_for_status()
        with open(out_file, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=8192):
                f.write(chunk)
    print(f"Downloaded: {out_file} ({out_file.stat().st_size / 1e6:.1f} MB)")
    
    asyncio.run(broadcast({
        "type": "trace",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "source": "gadm",
            "message": f"Successfully downloaded GADM boundaries file: {out_file.name} ({out_file.stat().st_size / 1e6:.1f} MB)"
        }
    }))
    return out_file

@task(name="import-gadm-to-db")
def import_gadm_to_db(gpkg_path: Path, region_id: str, admin_levels: list = [2, 3]) -> int:
    import geopandas as gpd
    from db.connection import SessionLocal
    from db.models import ZoneGeometry
    from geoalchemy2.shape import from_shape

    db = SessionLocal()
    total_imported = 0

    asyncio.run(broadcast({
        "type": "trace",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "source": "gadm",
            "message": f"Starting boundaries geo-processing and database import..."
        }
    }))

    try:
        # First check if zones are already imported to prevent duplicates
        existing_count = db.query(ZoneGeometry).filter(ZoneGeometry.region_id == region_id).count()
        if existing_count > 0:
            print("GADM zones already exist in database for this region. Skipping DB bulk save to prevent duplicate bounds.")
            asyncio.run(broadcast({
                "type": "trace",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "source": "gadm",
                    "message": f"GADM zones already exist in database ({existing_count} records). skipping save."
                }
            }))
            return existing_count

        for level in admin_levels:
            layer = f"ADM_ADM_{level}"
            try:
                gdf = gpd.read_file(gpkg_path, layer=layer)
                gdf = gdf.to_crs("EPSG:4326")
            except Exception as e:
                print(f"Could not read layer {layer}: {e}")
                asyncio.run(broadcast({
                    "type": "trace",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {
                        "source": "gadm",
                        "message": f"Failed reading level {level} layer: {str(e)}"
                    }
                }))
                continue

            zones = []
            from shapely.geometry import Polygon, MultiPolygon
            for _, row in gdf.iterrows():
                name_col  = f"NAME_{level}"
                gadm_col  = f"GID_{level}"
                
                geom = row.geometry
                if isinstance(geom, Polygon):
                    geom = MultiPolygon([geom])
                elif not isinstance(geom, MultiPolygon):
                    continue

                zone = ZoneGeometry(
                    id=str(uuid.uuid4()),
                    region_id=region_id,
                    admin_level=level,
                    name=str(row.get(name_col, "")),
                    gadm_gid=str(row.get(gadm_col, "")),
                    geometry=f"SRID=4326;{geom.wkt}",
                    source="gadm"
                )
                zones.append(zone)

            db.bulk_save_objects(zones)
            db.commit()
            total_imported += len(zones)
            print(f"Imported {len(zones)} zones at admin level {level}")
            
            asyncio.run(broadcast({
                "type": "trace",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "source": "gadm",
                    "message": f"Imported {len(zones)} boundaries for ADM Level {level}"
                }
            }))
            
        return total_imported
    except Exception as e:
        db.rollback()
        asyncio.run(broadcast({
            "type": "trace",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "source": "gadm",
                "message": f"Error saving GADM to database: {str(e)}"
            }
        }))
        raise e
    finally:
        db.close()

@flow(name="gadm-boundary-ingestion", log_prints=True)
def gadm_flow(country_iso3: str = None):
    flow_obj = GADMFlow()
    if not flow_obj.is_online():
        print("Offline - skipping GADM sync")
        return

    from db.connection import SessionLocal
    from db.models import Region
    db       = SessionLocal()
    region   = db.query(Region).filter(Region.is_active == True).first()
    db.close()

    if not region:
        print("No active region found.")
        return

    if not country_iso3:
        country_iso3 = region.country_code or "IND"

    gpkg_path = download_gadm(country_iso3)
    count = import_gadm_to_db(gpkg_path, str(region.id), admin_levels=[2, 3])
    
    flow_obj.update_source_sync_time()
    
    asyncio.run(broadcast({
        "type": "sync_status",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "source": "gadm",
            "layer_type": "boundaries",
            "count": count,
            "status": "success"
        }
    }))
    
    print("GADM boundary import complete")
    flow_obj.close()

if __name__ == "__main__":
    gadm_flow()
