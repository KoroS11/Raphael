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
