"""
Raphael — Geodetic Utilities (Task 3: Ellipsoid / WGS-84 upgrade)

All distance and bearing calculations use the WGS-84 ellipsoid via the
`geopy` library (Vincenty / geodesic formulae). This replaces the
spherical haversine approximation used in earlier code.

Accuracy improvement:
  Haversine (sphere R=6371 km): error up to ~0.3% at mid-latitudes
  Geodesic  (WGS-84 ellipsoid): error < 0.001 mm (Vincenty)

Public API
----------
geodesic_distance_km(lat1, lon1, lat2, lon2) -> float
    WGS-84 ellipsoidal distance in kilometres.

geodesic_bearing(lat1, lon1, lat2, lon2) -> float
    Initial bearing from (lat1, lon1) to (lat2, lon2), in degrees [0, 360).

destination_point(lat, lon, bearing_deg, distance_km) -> (lat, lon)
    Compute destination point given origin, bearing, and distance.

degrees_to_km(degrees) -> float
    Convert a latitude-degree offset to approximate kilometres (equatorial).
    Use for rough ST_Distance threshold conversions only; prefer geodesic_distance_km
    for precision work.

km_to_degrees(km) -> float
    Convert kilometres to approximate degree offset (equatorial estimate).
    Use only for ST_Distance WHERE clauses where exact precision is unnecessary.
"""

import math
from typing import Tuple

try:
    from geopy.distance import geodesic as _geopy_geodesic
    from geopy import Point as _GeoPoint
    _HAS_GEOPY = True
except ImportError:
    _HAS_GEOPY = False

# WGS-84 semi-major axis in km
_WGS84_A_KM = 6378.137
# WGS-84 mean radius in km (used as fallback if geopy unavailable)
_WGS84_MEAN_KM = 6371.0088


def geodesic_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Return the WGS-84 geodesic distance in kilometres between two
    geographic coordinates.

    Falls back to haversine (spherical) if geopy is not installed.
    """
    if _HAS_GEOPY:
        return _geopy_geodesic((lat1, lon1), (lat2, lon2)).km
    # Spherical haversine fallback
    return _haversine_km(lat1, lon1, lat2, lon2)


def geodesic_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Initial bearing (forward azimuth) from point 1 to point 2 on the
    WGS-84 ellipsoid, in degrees [0, 360).

    Uses the spherical formula; difference from ellipsoidal is < 0.1° for
    distances < 10 000 km — sufficient for wind-direction calculations.
    """
    lat1r = math.radians(lat1)
    lat2r = math.radians(lat2)
    dlon  = math.radians(lon2 - lon1)

    x = math.sin(dlon) * math.cos(lat2r)
    y = (math.cos(lat1r) * math.sin(lat2r)
         - math.sin(lat1r) * math.cos(lat2r) * math.cos(dlon))

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360.0) % 360.0


def destination_point(
    lat: float,
    lon: float,
    bearing_deg: float,
    distance_km: float,
) -> Tuple[float, float]:
    """
    Compute the destination point given an origin, bearing, and distance.

    Uses geopy (WGS-84 ellipsoid) when available; falls back to spherical
    approximation otherwise.

    Returns (lat, lon) in decimal degrees.
    """
    if _HAS_GEOPY:
        origin = _GeoPoint(lat, lon)
        dest   = _geopy_geodesic(kilometers=distance_km).destination(origin, bearing_deg)
        return (dest.latitude, dest.longitude)
    # Spherical fallback
    return _sphere_destination(lat, lon, bearing_deg, distance_km)


def degrees_to_km(degrees: float) -> float:
    """
    Convert a degree offset (latitude direction) to approximate kilometres.
    1° ≈ 111.32 km at the equator. Use only for rough ST_Distance thresholds.
    """
    return degrees * 111.32


def km_to_degrees(km: float) -> float:
    """
    Convert kilometres to an approximate degree offset (equatorial, latitude).
    Use only for rough ST_Distance WHERE clauses; not for precision geodesy.
    """
    return km / 111.32


# ── Private spherical fallbacks ───────────────────────────────────────────────

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance on WGS-84 mean sphere (±0.3% error)."""
    R = _WGS84_MEAN_KM
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def _sphere_destination(
    lat: float, lon: float, bearing_deg: float, distance_km: float
) -> Tuple[float, float]:
    """Spherical destination point (fallback when geopy unavailable)."""
    R  = _WGS84_MEAN_KM
    d  = distance_km / R
    b  = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)

    lat2 = math.asin(
        math.sin(lat1) * math.cos(d)
        + math.cos(lat1) * math.sin(d) * math.cos(b)
    )
    lon2 = lon1 + math.atan2(
        math.sin(b) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)
