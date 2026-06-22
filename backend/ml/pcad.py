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
        
        sy_m = _sigma_y(stability, dist_km * 1000.0)
        sz_m = _sigma_z(stability, dist_km * 1000.0)
        
        conc = centre_line_concentration(Q, u, dist_km * 1000.0, 
                                          5.0, stability)
        max_conc = max(max_conc, conc)
    
    return max_conc


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add temporal and rolling features for anomaly detection.
    Input df must have: value, observed_at, station_name columns.
    """
    df = df.copy()
    df['observed_at'] = pd.to_datetime(df['observed_at'])
    df = df.sort_values(['station_name', 'observed_at'])
    
    df['hour_of_day'] = df['observed_at'].dt.hour
    df['day_of_week'] = df['observed_at'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    
    # Per-station rolling features
    for stat in df['station_name'].unique():
        mask = df['station_name'] == stat
        vals = df.loc[mask, 'value']
        df.loc[mask, 'rolling_mean_3h'] = (
            vals.rolling(3, min_periods=1).mean()
        )
        df.loc[mask, 'rolling_std_3h'] = (
            vals.rolling(3, min_periods=1).std().fillna(0)
        )
        station_mean = vals.mean()
        station_std = vals.std()
        if station_std > 0:
            df.loc[mask, 'z_score'] = (
                (vals - station_mean) / station_std
            )
        else:
            df.loc[mask, 'z_score'] = 0.0
        df.loc[mask, 'delta_1h'] = vals.diff().fillna(0)
    
    le = LabelEncoder()
    df['station_id_encoded'] = le.fit_transform(df['station_name'])
    
    return df.dropna(subset=['rolling_mean_3h'])


def compute_pcad_scores(db: Session,
                         region_id: Optional[str] = None,
                         days_back: int = 7) -> pd.DataFrame:
    """
    Main PCAD function. Loads recent AQ data, computes
    physics features, runs IsolationForest, returns
    confidence-scored anomaly dataframe.
    
    Returns DataFrame with columns:
        station_name, observed_at, value, 
        if_anomaly (bool), plume_conc (float),
        confidence ('HIGH'|'MEDIUM'|'NORMAL'),
        anomaly_score (float)
    """
    if region_id is None:
        region_id = db.execute(text(
            "SELECT id FROM regions WHERE is_active=1 LIMIT 1"
        )).scalar()
    
    # Load AQ data
    rows = db.execute(text("""
        SELECT r.station_name, r.value, r.observed_at,
               json_extract(r.raw_payload, '$.lat') as lat,
               json_extract(r.raw_payload, '$.lon') as lon
        FROM raw_observations r
        WHERE r.region_id = :rid
        AND r.layer_type = 'aq'
        AND r.value > 0 AND r.value < 500
        AND r.observed_at > datetime('now', :days)
        ORDER BY r.observed_at
    """), {"rid": region_id, 
           "days": f"-{days_back} days"}).fetchall()
    
    if len(rows) < 20:
        log.warning(f"pcad_insufficient_data n_rows={len(rows)}")
        return pd.DataFrame()
    
    df = pd.DataFrame(rows, 
                      columns=['station_name', 'value', 
                                'observed_at', 'lat', 'lon'])
    df = engineer_features(df)
    
    # Load weather for plume feature
    weather = db.execute(text("""
        SELECT observed_at,
               MAX(CASE WHEN station_name = 'wind_speed_10m' THEN value END) as ws,
               MAX(CASE WHEN station_name = 'wind_direction_10m' THEN value END) as wd
        FROM raw_observations
        WHERE region_id = :rid
        AND layer_type = 'weather'
        AND observed_at > datetime('now', :days)
        GROUP BY observed_at
        ORDER BY observed_at
    """), {"rid": region_id,
           "days": f"-{days_back} days"}).fetchall()
    
    df_w = pd.DataFrame(weather, 
                         columns=['observed_at', 'ws', 'wd'])
    df_w['observed_at'] = pd.to_datetime(df_w['observed_at'])
    
    # Get zone centroids from DB (no hardcoding)
    zone_centroids = _get_zone_centroids(db)
    
    if not zone_centroids:
        log.error("pcad_no_zone_centroids")
        return pd.DataFrame()
    
    # Compute plume feature for each observation
    plume_concs = []
    for _, row in df.iterrows():
        # Find nearest weather within 1 hour
        if len(df_w) > 0:
            time_diff = abs(
                df_w['observed_at'] - 
                pd.Timestamp(row['observed_at'])
            )
            nearest_idx = time_diff.idxmin()
            if time_diff[nearest_idx] <= pd.Timedelta('1h'):
                ws = float(df_w.loc[nearest_idx, 'ws'] or 3.0)
            else:
                ws = 3.0
        else:
            ws = 3.0
        
        st_lat = float(row.get('lat') or 18.53)
        st_lon = float(row.get('lon') or 73.85)
        
        conc = compute_plume_feature(
            st_lat, st_lon, ws, 
            row['hour_of_day'],
            zone_centroids,
            source_pm25=float(row['value'])
        )
        plume_concs.append(conc)
    
    df['plume_conc'] = plume_concs
    df['stability_encoded'] = 0  # simplified for production
    
    # Standard features (Model A)
    feat_A = ['value', 'hour_of_day', 'day_of_week', 
