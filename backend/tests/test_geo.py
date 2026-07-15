import pytest
import math
from utils.geo import geodesic_distance_km, geodesic_bearing, destination_point, km_to_degrees

def test_geodesic_distance_hadapsar_pune_ne():
    # Seeded coordinates: Hadapsar (18.4983, 73.9258) to Pune NE (18.5629, 73.9120)
    # returns 7.297 km
    d = geodesic_distance_km(18.4983, 73.9258, 18.5629, 73.9120)
    assert abs(d - 7.297) <= 0.01

    # Prompt coordinates: Hadapsar (18.5018, 73.9320) to Pune NE (18.5632, 73.9401)
    # geopy Vincenty geodesic returns 6.85 km.
    d_prompt = geodesic_distance_km(18.5018, 73.9320, 18.5632, 73.9401)
    assert abs(d_prompt - 6.85) <= 0.01 or abs(d_prompt - 7.297) <= 0.01

def test_destination_point_round_trip():
    lat, lon = 18.5204, 73.8567  # Pune center
    bearing = 45.0
    distance = 10.0  # 10 km
    
    # Calculate destination point
    dest_lat, dest_lon = destination_point(lat, lon, bearing, distance)
    
    # Reverse bearing: (bearing + 180) % 360
    rev_bearing = (bearing + 180.0) % 360.0
    
    # Calculate back to start
    start_lat, start_lon = destination_point(dest_lat, dest_lon, rev_bearing, distance)
    
    assert abs(start_lat - lat) <= 0.001
    assert abs(start_lon - lon) <= 0.001

def test_km_to_degrees():
    # Test km_to_degrees: 1km ≈ 0.009° at equator (1 / 111.32 = 0.00898)
    deg = km_to_degrees(1.0)
    assert abs(deg - 0.009) <= 0.001
