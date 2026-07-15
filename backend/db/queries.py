import json
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from db.connection import IS_SPATIALITE

def get_observations_in_bbox(
    db: Session,
    layer_type: str,
    region_id: str,
    bbox: tuple,           # (west, south, east, north)
    hours_back: int = 6
) -> list:
    west, south, east, north = bbox
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    if IS_SPATIALITE:
        sql = text("""
            SELECT
                id,
                AsGeoJSON(geometry) as geom,
                value, unit, station_id, station_name,
                observed_at, source_id, is_anomalous, anomaly_score
            FROM raw_observations
            WHERE layer_type = :layer_type
              AND region_id  = :region_id
              AND observed_at >= :cutoff
              AND ST_Within(geometry,
                  SetSRID(BuildMbr(:west, :south, :east, :north), 4326))
            ORDER BY observed_at DESC
        """)
    else:
        sql = text("""
            SELECT
                id,
                ST_AsGeoJSON(geometry)::json as geom,
                value, unit, station_id, station_name,
                observed_at, source_id, is_anomalous, anomaly_score
            FROM raw_observations
            WHERE layer_type = :layer_type
              AND region_id  = :region_id
              AND observed_at >= :cutoff
              AND ST_Within(geometry,
                  ST_MakeEnvelope(:west, :south, :east, :north, 4326))
            ORDER BY observed_at DESC
        """)

    results = db.execute(sql, {
        "layer_type": layer_type,
        "region_id":  region_id,
        "cutoff":     cutoff,
        "west": west, "south": south,
        "east": east, "north": north
    }).fetchall()

    parsed_results = []
    for r in results:
        row_dict = dict(r._mapping)
        if IS_SPATIALITE and row_dict.get("geom"):
            try:
                row_dict["geom"] = json.loads(row_dict["geom"])
            except Exception:
                pass
        parsed_results.append(row_dict)
    return parsed_results


def get_observations_for_zone(
    db: Session,
    zone_id: str,
    layer_type: str,
    lookback_days: int = 90
) -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    if IS_SPATIALITE:
        sql = text("""
            SELECT strftime('%Y-%m-%d %H:00:00', o.observed_at) as ds, AVG(o.value) as y
            FROM raw_observations o
            JOIN zone_geometries z ON ST_Within(o.geometry, z.geometry)
            WHERE z.id = :zone_id
              AND o.layer_type = :layer_type
              AND o.observed_at >= :cutoff
            GROUP BY ds
            ORDER BY ds ASC
        """)
    else:
        sql = text("""
            SELECT DATE_TRUNC('hour', o.observed_at) as ds, AVG(o.value) as y
            FROM raw_observations o
            JOIN zone_geometries z ON ST_Within(o.geometry, z.geometry)
            WHERE z.id = :zone_id
              AND o.layer_type = :layer_type
              AND o.observed_at >= :cutoff
            GROUP BY ds
            ORDER BY ds ASC
        """)

    results = db.execute(sql, {
        "zone_id":    zone_id,
        "layer_type": layer_type,
        "cutoff":     cutoff
    }).fetchall()

    return [dict(r._mapping) for r in results]


def get_zone_current_indicators(db: Session, zone_id: str) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
    sql = text("""
        SELECT
            o.layer_type,
            AVG(o.value) as mean_value,
            MAX(o.observed_at) as latest_at
        FROM raw_observations o
        JOIN zone_geometries z ON ST_Within(o.geometry, z.geometry)
        WHERE z.id = :zone_id
          AND o.observed_at >= :cutoff
        GROUP BY o.layer_type
    """)
    result = db.execute(sql, {"zone_id": zone_id, "cutoff": cutoff}).fetchall()
    return {row.layer_type: {"value": row.mean_value, "at": row.latest_at}
            for row in result}


def get_active_region_bbox(db: Session) -> tuple:
    from db.models import Region
    from geoalchemy2.shape import to_shape
    region = db.query(Region).filter(
        Region.is_active == True
    ).first()
    if not region:
        return (76.8, 28.4, 77.4, 28.9)  # Delhi fallback only
    bounds = to_shape(region.bbox).bounds
    return bounds  # (west, south, east, north)


def get_active_region_centroid(db: Session) -> tuple:
    from db.models import Region
    from geoalchemy2.shape import to_shape
    region = db.query(Region).filter(
        Region.is_active == True
    ).first()
    if not region:
        return (28.6139, 77.2090)  # Delhi fallback only
    shape = to_shape(region.bbox)
    centroid = shape.centroid
    return (centroid.y, centroid.x)  # (lat, lon)


def get_zone_geometries_geojson(db: Session, region_id: str) -> dict:
    from db.connection import IS_SPATIALITE
    if IS_SPATIALITE:
        sql = text("""
            SELECT id, name, admin_level, gadm_gid, AsGeoJSON(geometry) as geom
            FROM zone_geometries
            WHERE region_id = :region_id
        """)
    else:
        sql = text("""
            SELECT id, name, admin_level, gadm_gid, ST_AsGeoJSON(geometry) as geom
            FROM zone_geometries
            WHERE region_id = :region_id
        """)
    results = db.execute(sql, {"region_id": region_id}).fetchall()
    features = []
    for r in results:
        geom_str = r.geom
        geom = json.loads(geom_str) if geom_str else None
        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "id": str(r.id),
                "name": r.name,
                "admin_level": r.admin_level,
                "gadm_gid": r.gadm_gid
            }
        })
    return {
        "type": "FeatureCollection",
        "features": features
    }
