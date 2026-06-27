import sys
import os
import uuid
from datetime import datetime, timezone
import bcrypt
from shapely.geometry import box, MultiPolygon
from geoalchemy2.shape import from_shape

# Add backend to sys.path so we can import from db
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "backend"))

from db.connection import SessionLocal, engine, IS_SPATIALITE
from db.models import User, Source, Region, ZoneGeometry

# ---------------------------------------------------------------------------
# Pune zone definitions — centroid (lat, lon) and approximate rectangular
# polygon extents. Each is ~0.02° × 0.02° around its centroid.
# TODO: Replace with real ward/district GeoJSON boundaries from GADM or
# Pune Municipal Corporation open data when available.
# ---------------------------------------------------------------------------
PUNE_ZONES = [
    {
        "name": "Hadapsar Industrial",
        "name_local": "हडपसर",
        "lat": 18.4983, "lon": 73.9258,
        "admin_level": 3,
    },
    {
        "name": "Pune NE Quadrant",
        "name_local": "पुणे ईशान्य",
        "lat": 18.5629, "lon": 73.9120,
        "admin_level": 3,
    },
    {
        "name": "Kothrud Residential",
        "name_local": "कोथरूड",
        "lat": 18.5074, "lon": 73.8077,
        "admin_level": 3,
    },
    {
        "name": "Katraj Hills",
        "name_local": "कात्रज",
        "lat": 18.4529, "lon": 73.8567,
        "admin_level": 3,
    },
    {
        "name": "Shivajinagar",
        "name_local": "शिवाजीनगर",
        "lat": 18.5310, "lon": 73.8446,
        "admin_level": 3,
    },
    {
        "name": "Aundh",
        "name_local": "औंध",
        "lat": 18.5590, "lon": 73.8070,
        "admin_level": 3,
    },
]


def _make_zone_geom(lat: float, lon: float, half_deg: float = 0.01):
    """Create a small rectangular MULTIPOLYGON around a centroid."""
    rect = box(lon - half_deg, lat - half_deg, lon + half_deg, lat + half_deg)
    return MultiPolygon([rect])


def _geom_value(shapely_geom, srid=4326):
    """Return a geometry value suitable for the current DB backend."""
    if IS_SPATIALITE:
        return f"SRID={srid};{shapely_geom.wkt}"
    return from_shape(shapely_geom, srid=srid)


def _make_id():
    return uuid.uuid4()


def seed_demo(fresh: bool = False):
    db = SessionLocal()
    try:
        if fresh:
            print("FRESH mode: purging zone_geometries, regions...")
            db.query(ZoneGeometry).delete()
            db.query(Region).delete()
            db.commit()
            print("  Purged.")

        # 1. Create admin user if it doesn't exist
        existing_admin = db.query(User).filter_by(username="admin").first()
        if not existing_admin:
            admin = User(
                id=_make_id(),
                username="admin",
                password_hash=bcrypt.hashpw("raphael_admin".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
                display_name="Administrator",
                role="admin",
                organization="Raphael"
            )
            db.add(admin)
            print("Seeded admin user.")
        else:
            print("Admin user already exists.")

        # 2. Create regions: Pune PMR (active) + Delhi NCT (inactive)
        pune_id = _make_id()
        delhi_id = _make_id()

        existing_pune = db.query(Region).filter_by(name="Pune Metropolitan Region").first()
        if not existing_pune:
            pune_bbox = box(73.7, 18.4, 74.0, 18.65)
            pune = Region(
                id=pune_id,
                name="Pune Metropolitan Region",
                country_code="IN",
                bbox=_geom_value(pune_bbox),
                admin_level=2,
                is_active=True
            )
            db.add(pune)
            print("Seeded Pune Metropolitan Region (active).")
        else:
            pune_id = existing_pune.id
            print("Pune region already exists.")

        existing_delhi = db.query(Region).filter_by(name="Delhi NCT").first()
        if not existing_delhi:
            delhi_bbox = box(76.8, 28.4, 77.4, 28.9)
            delhi = Region(
                id=delhi_id,
                name="Delhi NCT",
                country_code="IN",
                bbox=_geom_value(delhi_bbox),
                admin_level=2,
                is_active=False
            )
            db.add(delhi)
            print("Seeded Delhi NCT (inactive).")
        else:
            print("Delhi NCT already exists.")

        # 3. Seed Pune zones
        existing_zone_count = db.query(ZoneGeometry).filter(
            ZoneGeometry.region_id == pune_id
        ).count()

        if existing_zone_count == 0:
            for zdef in PUNE_ZONES:
                geom = _make_zone_geom(zdef["lat"], zdef["lon"])
                zone = ZoneGeometry(
                    id=_make_id(),
                    region_id=pune_id,
                    admin_level=zdef["admin_level"],
                    name=zdef["name"],
                    name_local=zdef["name_local"],
                    gadm_gid=None,
                    geometry=_geom_value(geom),
                    properties={"centroid_lat": zdef["lat"], "centroid_lon": zdef["lon"]},
                    source="seed",
                )
                db.add(zone)
            print(f"Seeded {len(PUNE_ZONES)} Pune zones.")
        else:
            print(f"Pune zones already exist ({existing_zone_count} found).")

        # 4. Create default sources
        default_sources = [
            ('openaq',          'OpenAQ v3',                    'air_quality',  ['aq']),
            ('waqi',            'World AQI',                    'air_quality',  ['aq']),
            ('iqair',           'IQAir AirVisual',              'air_quality',  ['aq']),
            ('copernicus_cams', 'Copernicus CAMS',              'air_quality',  ['aq']),
            ('open_meteo',      'Open-Meteo',                   'weather',      ['weather', 'precipitation']),
            ('noaa_gfs',        'NOAA GFS',                     'weather',      ['weather']),
            ('openweathermap',  'OpenWeatherMap',               'weather',      ['weather']),
            ('copernicus_era5', 'ERA5 Reanalysis',              'climate',      ['climate']),
            ('nasa_firms',      'NASA FIRMS VIIRS',             'fire',         ['fire']),
            ('nasa_lance',      'NASA LANCE NRT',               'fire',         ['fire']),
            ('modis_lst',       'NASA MODIS LST',               'satellite',    ['lst']),
            ('modis_ndvi',      'NASA MODIS NDVI',              'satellite',    ['ndvi']),
            ('sentinel2',       'Copernicus Sentinel-2',        'satellite',    ['ndvi']),
            ('usgs_landsat',    'USGS Earth Explorer Landsat',  'satellite',    ['ndvi', 'lst']),
            ('gfw',             'Global Forest Watch',          'vegetation',   ['ndvi']),
            ('hansen',          'Hansen Forest Change',         'vegetation',   ['ndvi']),
            ('gadm',            'GADM Boundaries',              'geospatial',   ['boundaries']),
            ('overpass',        'OpenStreetMap Overpass',        'geospatial',   ['urban']),
            ('ghsl',            'GHSL Built-up Layer',          'geospatial',   ['urban']),
            ('worldpop',        'WorldPop Density',             'geospatial',   ['population']),
            ('nasa_sedac',      'NASA SEDAC',                   'geospatial',   ['socioeconomic']),
            ('datameet',        'Datameet India',               'geospatial',   ['boundaries']),
            ('gdacs',           'GDACS Disaster Alerts',        'hazard',       ['hazard']),
            ('fema_flood',      'FEMA Flood Zones',             'hazard',       ['hazard']),
            ('emdat',           'EM-DAT Disaster DB',           'hazard',       ['hazard']),
            ('noaa_ncei',       'NOAA NCEI Events',             'hazard',       ['hazard'])
        ]

        seeded_sources_count = 0
        for key, name, category, layers in default_sources:
            existing_src = db.query(Source).filter_by(key=key).first()
            if not existing_src:
                src = Source(
                    id=_make_id(),
                    key=key,
                    name=name,
                    category=category,
                    layer_types=layers
                )
                db.add(src)
                seeded_sources_count += 1
        
        if seeded_sources_count > 0:
            print(f"Seeded {seeded_sources_count} default sources.")
        else:
            print("All default sources already exist.")

        db.commit()
        print("\nDemo seed complete successfully.")
        print("Admin user: admin / raphael_admin")

        # Final summary
        region_count = db.query(Region).count()
        zone_count = db.query(ZoneGeometry).count()
        print(f"Regions: {region_count}, Zones: {zone_count}")

    except Exception as e:
        db.rollback()
        print("Error seeding database:", e)
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    is_fresh = "--fresh" in sys.argv
    seed_demo(fresh=is_fresh)
