"""
Raphael — Stage 5: DISPERSE (Gaussian Plume Model)

Computes pollutant dispersion from point sources (anomalous AQ stations)
using the Gaussian Plume equation. Stores plume centre-line concentration
estimates as ml_outputs rows with model_type='gaussian_plume'.

Physics reference:
  C(x, y, z) = Q / (2π·u·σy·σz)
              * exp(-y²/(2·σy²))
              * [exp(-(z-H)²/(2·σz²)) + exp(-(z+H)²/(2·σz²))]

  Where:
    C  = concentration at receptor (μg/m³)
    Q  = emission rate  (μg/s)
    u  = mean wind speed (m/s)
    σy = horizontal dispersion (m)  — Pasquill-Gifford stability class
    σz = vertical dispersion   (m)
    H  = effective stack height (m)
    x  = downwind distance (m)
    y  = crosswind distance (m)   — 0 for centre-line
    z  = receptor height (m)      — 0 for ground level

Pasquill-Gifford (PG) coefficients after Green & Singhal (1980) look-up
table for stability classes A–F, downwind distances 100 m – 50 km.

Output rows (ml_outputs):
  model_type  = 'gaussian_plume'
  output_type = 'centre_line_concentration'
  layer_type  = 'aq'
  value       = estimated ground-level concentration (μg/m³)
  explanation = JSON-serialised plume parameters
  geometry    = receptor point (WGS-84) at plume distances
"""

import uuid
import json
import math
import numpy as np
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from utils.geo import geodesic_distance_km, destination_point
import structlog

log = structlog.get_logger()

# ── Pasquill-Gifford dispersion coefficients ─────────────────────────────────
#
# σy = a · x^b     (horizontal, x in metres)
# σz = c · x^d     (vertical,   x in metres, x in km range)
#
# Stability classes: A=very unstable, B=unstable, C=slightly unstable,
#                    D=neutral,       E=stable,   F=very stable
#
# Coefficients from Turner (1994) workbook Table B-2

PG_SIGMA_Y = {
    "A": (0.3658, 0.9024),
    "B": (0.2751, 0.9024),
    "C": (0.2090, 0.9024),
    "D": (0.1471, 0.9024),
    "E": (0.1046, 0.9024),
    "F": (0.0722, 0.9024),
}

PG_SIGMA_Z = {
    #  class: (c, d)  — σz = c * x^d  (x in metres)
    "A": (0.192,  0.936),
    "B": (0.156,  0.922),
    "C": (0.116,  0.905),
    "D": (0.079,  0.881),
    "E": (0.063,  0.871),
    "F": (0.053,  0.814),
}

# Maximum σz cap to avoid unphysical values
SIGMA_Z_MAX = 5000.0  # metres


def _pg_class_from_wind(wind_speed_ms: float, daytime: bool = True) -> str:
    """
    Estimate Pasquill-Gifford stability class from wind speed.
    Simplified Pasquill (1961) categorisation — class D (neutral) for night.
    """
    if not daytime:
        if wind_speed_ms < 2:
            return "F"
        if wind_speed_ms < 3:
            return "E"
        return "D"

    if wind_speed_ms < 2:
        return "A"
    if wind_speed_ms < 3:
        return "B"
    if wind_speed_ms < 5:
        return "C"
    if wind_speed_ms < 6:
        return "D"
    return "D"


def _sigma_y(pg_class: str, x_m: float) -> float:
    a, b = PG_SIGMA_Y[pg_class]
    return a * (x_m ** b)


def _sigma_z(pg_class: str, x_m: float) -> float:
    c, d = PG_SIGMA_Z[pg_class]
    return min(c * (x_m ** d), SIGMA_Z_MAX)


def centre_line_concentration(
    Q: float,       # emission rate μg/s
    u: float,       # wind speed m/s
    x_m: float,     # downwind distance m
    H: float = 10.0,  # effective stack height m
    pg_class: str = "D",
) -> float:
    """
    Ground-level centre-line Gaussian Plume concentration (μg/m³).
    Returns 0 if wind speed is too low (< 0.5 m/s) to avoid division-by-zero.
    """
    if u < 0.5 or x_m < 1.0:
        return 0.0

    sy = _sigma_y(pg_class, x_m)
    sz = _sigma_z(pg_class, x_m)

    if sy < 1e-6 or sz < 1e-6:
        return 0.0

    C = (Q / (math.pi * u * sy * sz)) * math.exp(-(H ** 2) / (2 * sz ** 2))
    return max(0.0, C)


def _receptor_point(src_lat, src_lon, bearing_deg, distance_km):
    """
    Compute receptor (lat, lon) given source, bearing and distance.
    Delegates to utils.geo.destination_point (WGS-84 ellipsoid via geopy,
    spherical fallback if geopy unavailable).
    """
    return destination_point(src_lat, src_lon, bearing_deg, distance_km)


# ── Default receptor distances along the plume axis ──────────────────────────
RECEPTOR_DISTANCES_KM = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]


def run_gaussian_plume(db: Session, region_id: str) -> List[dict]:
    """
    Stage 5 — DISPERSE.

    For each anomalous AQ station in the active region (last 24 h):
      1. Retrieve latest PM2.5 value and derive Q (emission proxy).
      2. Fetch wind speed from weather observations.
      3. Compute centre-line concentrations at RECEPTOR_DISTANCES_KM.
      4. Persist one ml_outputs row per receptor point.

    Returns a list of result dicts (one per plume row written).
    """
    from db.models import MLOutput

    # ── 1. Find anomalous AQ stations ────────────────────────────────────────
    sources = db.execute(text("""
        SELECT
            o.station_id,
            o.station_name,
            AVG(o.value)            AS pm25,
            ST_X(o.geometry)        AS lon,
            ST_Y(o.geometry)        AS lat,
            COUNT(*)                AS n_obs
        FROM raw_observations o
        WHERE o.region_id   = :region_id
          AND o.layer_type  = 'aq'
          AND o.is_anomalous = 1
          AND o.observed_at >= datetime('now', '-24 hours')
          AND o.geometry IS NOT NULL
        GROUP BY o.station_id, o.station_name, o.geometry
        HAVING COUNT(*) >= 1
        LIMIT 10
    """), {"region_id": region_id}).fetchall()

    if not sources:
        log.info("gaussian_plume_skip", reason="No anomalous AQ stations in last 24h")
        return []

    # ── 2. Wind speed from weather observations ───────────────────────────────
    wind_row = db.execute(text("""
        SELECT value
        FROM raw_observations
        WHERE region_id = :region_id
          AND layer_type = 'weather'
          AND (unit LIKE '%m/s%' OR unit LIKE '%wind%' OR station_name LIKE '%wind%')
          AND observed_at >= datetime('now', '-6 hours')
        ORDER BY observed_at DESC
        LIMIT 1
    """), {"region_id": region_id}).fetchone()

    wind_speed_ms = float(wind_row.value) if wind_row and wind_row.value else 3.5
    wind_speed_ms = max(0.5, min(wind_speed_ms, 30.0))  # clamp

    # Wind direction: default to north (360°) if unavailable
    wind_dir_row = db.execute(text("""
        SELECT value FROM raw_observations
        WHERE region_id  = :region_id
          AND layer_type = 'weather'
          AND (unit LIKE '%deg%' OR unit LIKE '%direction%')
          AND observed_at >= datetime('now', '-6 hours')
        ORDER BY observed_at DESC LIMIT 1
    """), {"region_id": region_id}).fetchone()

    wind_dir_deg = float(wind_dir_row.value) if wind_dir_row and wind_dir_row.value else 270.0
    # Plume disperses downwind of source — bearing = wind_dir (from) + 180
    plume_bearing = (wind_dir_deg + 180.0) % 360.0

    # ── 3. Current hour: daytime flag ─────────────────────────────────────────
    utc_hour = datetime.now(timezone.utc).hour
    daytime = 6 <= utc_hour < 20

    pg_class = _pg_class_from_wind(wind_speed_ms, daytime)

    # ── 4. Delete old plume outputs for this region ───────────────────────────
    db.execute(text("""
        DELETE FROM ml_outputs
        WHERE model_type = 'gaussian_plume'
          AND zone_id IN (
              SELECT id FROM zone_geometries WHERE region_id = :region_id
          )
    """), {"region_id": region_id})

    outputs = []
    results = []

    for src in sources:
        src_lat = float(src.lat)
        src_lon = float(src.lon)
        pm25    = float(src.pm25 or 0.0)

        if pm25 <= 0:
            continue

        # Emission rate proxy: 1 μg/m³ of PM2.5 ≈ 1 μg/s per station
        URBAN_BASELINE_Q = 50000.0
        Q_computed = pm25 * 1000.0 if pm25 > 0 else URBAN_BASELINE_Q
        Q = max(1000.0, min(500000.0, Q_computed))

        # Effective stack height: assume ground-level sources (H = 5 m)
        H = 5.0

        for dist_km in RECEPTOR_DISTANCES_KM:
            dist_m = dist_km * 1000.0
            C = centre_line_concentration(Q, wind_speed_ms, dist_m, H, pg_class)

            rec_lat, rec_lon = _receptor_point(src_lat, src_lon, plume_bearing, dist_km)

            # Nearest zone to receptor (best-effort)
            zone_row = db.execute(text("""
                SELECT id FROM zone_geometries
                WHERE region_id = :region_id
                ORDER BY ST_Distance(
                    MakePoint(:lon, :lat, 4326),
                    Centroid(geometry)
                ) ASC
                LIMIT 1
            """), {"region_id": region_id, "lat": rec_lat, "lon": rec_lon}).fetchone()

            zone_id = str(zone_row.id) if zone_row else None

            explanation = json.dumps({
                "source_station":  src.station_name,
                "source_pm25":     round(pm25, 1),
                "emission_proxy_Q": round(Q, 1),
                "wind_speed_ms":   round(wind_speed_ms, 1),
                "wind_dir_deg":    round(wind_dir_deg, 1),
                "pg_stability":    pg_class,
                "distance_km":     dist_km,
                "stack_height_m":  H,
                "sigma_y_m":       round(_sigma_y(pg_class, dist_m), 1),
                "sigma_z_m":       round(_sigma_z(pg_class, dist_m), 1),
            })

            row = MLOutput(
                id=uuid.uuid4(),
                zone_id=zone_id,
                geometry=f"SRID=4326;POINT({rec_lon} {rec_lat})",
                model_type="gaussian_plume",
                output_type="centre_line_concentration",
                layer_type="aq",
                value=round(C, 3),
                explanation=explanation,
                model_version="gauss-pg-v1.0",
                computed_at=datetime.now(timezone.utc),
            )
            outputs.append(row)
            results.append({
                "source_station": src.station_name,
                "distance_km":    dist_km,
                "receptor_lat":   round(rec_lat, 6),
                "receptor_lon":   round(rec_lon, 6),
                "concentration":  round(C, 3),
                "pg_class":       pg_class,
                "wind_speed_ms":  round(wind_speed_ms, 1),
            })

    if outputs:
        db.bulk_save_objects(outputs)
        db.commit()

    log.info(
        "gaussian_plume_complete",
        sources=len(sources),
        receptors=len(outputs),
        wind_ms=round(wind_speed_ms, 1),
        pg_class=pg_class,
    )
    return results
