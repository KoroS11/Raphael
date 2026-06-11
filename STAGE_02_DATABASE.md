# Stage 02 — Database Setup

## Prerequisites
Stage 01 completed. Python venv active.

## Objective
Set up the geospatial database, run all migrations, and verify spatial queries work. The application auto-selects PostGIS or SpatiaLite based on available RAM.

---

## Step 1 — Install Alembic and Initialize Migrations

With the backend venv active:

```
cd backend
alembic init db/migrations
```

Replace `db/migrations/env.py` with:

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from db.models import Base
from db.connection import DATABASE_URL

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
```

---

## Step 2 — Create Database Connection Module

Create `backend/db/connection.py`:

```python
import os
import platform
import psutil
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

def get_available_ram_gb() -> float:
    return psutil.virtual_memory().available / (1024 ** 3)

def get_database_url() -> str:
    ram = get_available_ram_gb()
    threshold = float(os.getenv("DB_RAM_THRESHOLD_GB", "6"))

    if ram >= threshold:
        user     = os.getenv("POSTGRES_USER", "raphael")
        password = os.getenv("POSTGRES_PASSWORD", "raphael")
        host     = "127.0.0.1"
        port     = os.getenv("POSTGRES_PORT", "5433")
        db       = os.getenv("POSTGRES_DB", "raphael_db")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    else:
        data_dir = os.getenv("RAPHAEL_DATA_DIR", "./data")
        return f"sqlite+pysqlite:///{data_dir}/raphael.db"

DATABASE_URL = get_database_url()
IS_SPATIALITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SPATIALITE else {}
)

if IS_SPATIALITE:
    @event.listens_for(engine, "connect")
    def load_spatialite(dbapi_conn, connection_record):
        dbapi_conn.enable_load_extension(True)
        dbapi_conn.load_extension("mod_spatialite")
        dbapi_conn.enable_load_extension(False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Install psutil:
```
pip install psutil
```

---

## Step 3 — Create SQLAlchemy ORM Models

Create `backend/db/models.py` with the full ORM model definitions matching every table in `docs/TECHNICAL_SPECIFICATION.md` Section 4.

Key models to implement: User, ActivityLog, Region, Source, RawObservation, ZoneGeometry, RasterTile, MLOutput, AlertRule, AlertEvent, ImportDataset, EventMarker.

Every geometry column must use GeoAlchemy2's `Geometry` type:

```python
from geoalchemy2 import Geometry
from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

class RawObservation(Base):
    __tablename__ = "raw_observations"
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id    = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    region_id    = Column(UUID(as_uuid=True), ForeignKey("regions.id"), nullable=False)
    layer_type   = Column(String(50), nullable=False)
    geometry     = Column(Geometry("POINT", srid=4326), nullable=False)
    value        = Column(Float, nullable=False)
    unit         = Column(String(20))
    station_id   = Column(String(100))
    station_name = Column(String(200))
    observed_at  = Column(DateTime(timezone=True), nullable=False)
    synced_at    = Column(DateTime(timezone=True))
    raw_payload  = Column(JSONB)
    is_anomalous = Column(Boolean, default=False)
    anomaly_score= Column(Float)
```

Define all remaining models following the same pattern.

---

## Step 4 — Create the Migration Script

Create `backend/db/migrations/versions/001_initial_schema.py`:

Copy the full SQL from `docs/TECHNICAL_SPECIFICATION.md` Section 4 and wrap it as an Alembic migration:

```python
def upgrade():
    op.execute("""
        -- Full SQL from TECHNICAL_SPECIFICATION.md Section 4 goes here
        -- All CREATE TABLE, CREATE INDEX, and INSERT statements
    """)

def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS activity_log CASCADE;
        DROP TABLE IF EXISTS event_markers CASCADE;
        DROP TABLE IF EXISTS import_datasets CASCADE;
        DROP TABLE IF EXISTS alert_events CASCADE;
        DROP TABLE IF EXISTS alert_rules CASCADE;
        DROP TABLE IF EXISTS ml_outputs CASCADE;
        DROP TABLE IF EXISTS raster_tiles CASCADE;
        DROP TABLE IF EXISTS raw_observations CASCADE;
        DROP TABLE IF EXISTS zone_geometries CASCADE;
        DROP TABLE IF EXISTS regions CASCADE;
        DROP TABLE IF EXISTS sources CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
    """)
```

---

## Step 5 — Run Migrations

For SpatiaLite (low RAM):
```
cd backend
python -c "
from db.connection import engine
from db.connection import load_spatialite
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text('SELECT InitSpatialMetaData()'))
    conn.commit()
"
alembic upgrade head
```

For PostGIS (high RAM):

First create the database:
```
psql -U postgres -p 5433 -c "CREATE USER raphael WITH PASSWORD 'raphael';"
psql -U postgres -p 5433 -c "CREATE DATABASE raphael_db OWNER raphael;"
psql -U postgres -p 5433 -d raphael_db -c "CREATE EXTENSION postgis;"
```

Then run migrations:
```
alembic upgrade head
```

---

## Step 6 — Create the Seed Script

Create `scripts/seed.py`:

```python
import sys
import uuid
from datetime import datetime, timezone
sys.path.insert(0, "backend")

from db.connection import SessionLocal
from db.models import User, Source, Region
from passlib.context import CryptContext
from shapely.geometry import box
from geoalchemy2.shape import from_shape

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed_demo():
    db = SessionLocal()
    try:
        # Create admin user
        admin = User(
            id=uuid.uuid4(),
            username="admin",
            password_hash=pwd_context.hash("raphael_admin"),
            display_name="Administrator",
            role="admin",
            organization="Raphael"
        )
        db.add(admin)

        # Create demo region (Delhi)
        delhi_bbox = box(76.8, 28.4, 77.4, 28.9)
        delhi = Region(
            id=uuid.uuid4(),
            name="Delhi NCT",
            country_code="IND",
            bbox=from_shape(delhi_bbox, srid=4326),
            admin_level=2,
            is_active=True
        )
        db.add(delhi)

        db.commit()
        print("Seed complete. Admin password: raphael_admin")
        print("IMPORTANT: Change this password on first login.")
    finally:
        db.close()

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "dev"
    seed_demo()
```

Run the seed:
```
python scripts/seed.py --mode dev
```

---

## Step 7 — Create Spatial Query Helpers

Create `backend/db/queries.py` with the key spatial query functions used by the API and ML layers:

```python
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from .models import RawObservation, ZoneGeometry, MLOutput

def get_observations_in_bbox(
    db: Session,
    layer_type: str,
    region_id: str,
    bbox: tuple,           # (west, south, east, north)
    hours_back: int = 6
) -> list:
    west, south, east, north = bbox
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    return db.execute(text("""
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
