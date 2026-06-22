"""
PCAD — Physics-Corroborated Anomaly Detection
Integrates Gaussian Plume dispersion physics with IsolationForest
anomaly detection to produce confidence-scored anomaly flags.

Based on RAPHAEL research notebooks validated on Pune PM2.5 data.
Novel contribution: using dispersion physics as ML feature.

Reference: RAPHAEL architecture paper (2026)
"""

import os
import pickle
import logging
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
from sqlalchemy.orm import Session
from sqlalchemy import text

log = logging.getLogger(__name__)

# Recommended contamination from Notebook 1 tuning
RECOMMENDED_CONTAMINATION = 0.05  # Update after notebook results

# PCAD corroboration threshold (μg/m³)
# After Q proxy fix, plume concentrations should be 10-100 μg/m³
CORROBORATION_THRESHOLD = 15.0


def _get_zone_centroids(db: Session) -> dict:
    """
    Query zone centroids from database — NO hardcoding.
    Returns: {zone_name: (lat, lon)}
    """
    rows = db.execute(text("""
        SELECT name, ST_Y(Centroid(geometry)), ST_X(Centroid(geometry))
        FROM zone_geometries
        WHERE region_id = (
            SELECT id FROM regions WHERE is_active = 1 LIMIT 1
        )
    """)).fetchall()
    
    if not rows:
        log.warning("pcad_no_zones_found_in_db")
        return {}
    
    return {row[0]: (float(row[1]), float(row[2])) 
            for row in rows}


def _haversine_km(lat1: float, lon1: float, 
                   lat2: float, lon2: float) -> float:
    """WGS-84 approximate distance in km."""
    try:
        from geopy.distance import geodesic
        return geodesic((lat1, lon1), (lat2, lon2)).km
    except Exception:
        import math
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2)**2 + 
             math.cos(math.radians(lat1)) * 
             math.cos(math.radians(lat2)) * 
             math.sin(dlon/2)**2)
        return R * 2 * math.asin(math.sqrt(max(0, a)))


def compute_plume_feature(station_lat: float, station_lon: float,
                            wind_speed: float, obs_hour: int,
                            zone_centroids: dict,
                            source_pm25: float = 50.0) -> float:
    """
    Compute maximum Gaussian Plume concentration at a station
    from any zone source given wind conditions.
    
    Returns concentration in μg/m³ (realistic range: 0.1-500)
    """
    from ml.plume import (_pg_class_from_wind, 
                           _sigma_y, _sigma_z,
                           centre_line_concentration)
    
    solar = 'moderate' if 6 <= obs_hour <= 18 else 'night'
    stability = _pg_class_from_wind(max(wind_speed, 0.5), solar)
    
    # Realistic Q proxy: source_pm25 * 1000 μg/s
    # Capped between 1000 and 500000 μg/s
    Q = max(1000.0, min(500000.0, source_pm25 * 1000))
    u = max(wind_speed, 0.5)
    
    max_conc = 0.0
    
    for zone_name, (z_lat, z_lon) in zone_centroids.items():
        dist_km = _haversine_km(z_lat, z_lon, 
                                 station_lat, station_lon)
        if dist_km < 0.1:
            continue
