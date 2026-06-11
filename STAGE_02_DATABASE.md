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
