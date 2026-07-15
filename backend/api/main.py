import sys, os

# Windows DLL overrides for MKL/OMP, Stan compiler, and SpatiaLite
if sys.platform == 'win32':
    conda_prefix = os.environ.get("RAPHAEL_CONDA_PREFIX") or os.environ.get("CONDA_PREFIX") or r"C:\Users\harsh\anaconda3\envs\raphael-env"
    lib_bin = os.path.join(conda_prefix, "Library", "bin")
    if os.path.exists(lib_bin):
        if lib_bin not in os.environ["PATH"]:
            os.environ["PATH"] = lib_bin + os.pathsep + os.environ["PATH"]
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(lib_bin)
            except Exception:
                pass

# Monkeypatch Windows SSL default cert loading to bypass ASN1 NOT_ENOUGH_DATA certificate store bug
import ssl
orig_load_default_certs = ssl.SSLContext.load_default_certs
def patched_load_default_certs(self, purpose=ssl.Purpose.SERVER_AUTH):
    try:
        return orig_load_default_certs(self, purpose)
    except Exception:
        try:
            import certifi
            self.load_verify_locations(certifi.where())
        except Exception:
            pass
ssl.SSLContext.load_default_certs = patched_load_default_certs

# Pre-import torch first to resolve Windows OpenMP/MKL DLL collision quirk
try:
    import torch
except Exception:
    pass


import ssl
try:
    orig_load_windows_store_certs = ssl.SSLContext._load_windows_store_certs
    def patched_load_windows_store_certs(self, storename, purpose):
        try:
            orig_load_windows_store_certs(self, storename, purpose)
        except ssl.SSLError:
            pass
    ssl.SSLContext._load_windows_store_certs = patched_load_windows_store_certs
except AttributeError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import sys
import signal
from sqlalchemy import text

from .routes import regions, layers, zones, alerts, imports, reports, users, system, ws, geocode, anomalies, risk

from db.connection import engine, DATABASE_URL
from db.models import Base
from api.logging_config import configure_production_logging

# Configure logging at startup
configure_production_logging()

def run_alembic_migrations():
    from alembic.config import Config
    from alembic import command
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # points to backend/
    ini_path = os.path.join(base_dir, "alembic.ini")
    
    config = Config(ini_path)
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    config.set_main_option("script_location", os.path.join(base_dir, "db", "migrations"))
    
    print("Running database migrations programmatically...")
    try:
        command.upgrade(config, "head")
        print("Database migrations run successfully.")
    except Exception as e:
        if "already exists" in str(e):
            # Database was created outside Alembic — stamp it as current
            print(f"Tables already exist, stamping alembic version to head: {e}")
            try:
                command.stamp(config, "head")
                print("Database stamped at head successfully.")
            except Exception as stamp_err:
                print(f"Warning: Could not stamp database: {stamp_err}")
        else:
            print(f"Critical: Database migration failed: {e}")
            sys.exit(1)

def run_startup_self_test():
    from db.connection import SessionLocal
    db = SessionLocal()
    print("Executing startup database self-tests...")
    tables = ["raw_observations", "ml_outputs", "zone_geometries", "alert_rules"]
    for table in tables:
        try:
            db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
            print(f"Self-test query succeeded for table: {table}")
        except Exception as e:
            error_msg = f"Critical: Database self-test failed for table '{table}': {e}"
            print(error_msg)
            db.close()
            sys.exit(1)
            
    # Spatial query self-test
    try:
        try:
            db.execute(text("SELECT ST_AsText(geometry) FROM raw_observations LIMIT 1"))
        except Exception:
            db.execute(text("SELECT AsText(geometry) FROM raw_observations LIMIT 1"))
        print("Self-test spatial query succeeded.")
    except Exception as e:
        error_msg = f"Critical: Database self-test failed for spatial query: {e}"
        print(error_msg)
        db.close()
        sys.exit(1)
        
    db.close()
    print("Startup database self-tests passed.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Raphael API starting...")
    # 1. Run migrations
    run_alembic_migrations()
    
    # 2. Run basic DB initialization fallback
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables ensured.")
    except Exception as e:
        print(f"Error ensuring database tables: {e}")
        
    # 3. Run self-tests
    run_startup_self_test()
    yield
    # Shutdown
    print("Raphael API shutting down...")

app = FastAPI(
    title="Raphael Environmental Intelligence API",
    version="1.0.0",
    lifespan=lifespan
)

# Graceful shutdown handler
def shutdown_handler(signum, frame):
    print(f"Received signal {signum}. Disposing database connections and exiting...")
    try:
        engine.dispose()
        print("Database connection pool disposed cleanly.")
    except Exception as e:
        print(f"Error disposing connection pool: {e}")
    sys.exit(0)

# Register signal handlers
try:
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
except ValueError:
    # Occurs when running in non-main threads during testing
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:1420",
        "tauri://localhost",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:1420"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount tiles static directory for HTTP Range request vector tile loading
data_dir = os.getenv("RAPHAEL_DATA_DIR")
if not data_dir:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data")
tiles_dir = os.path.join(data_dir, "tiles")
os.makedirs(tiles_dir, exist_ok=True)
app.mount("/tiles", StaticFiles(directory=tiles_dir), name="tiles")

app.include_router(regions.router, prefix="/api/v1/regions",   tags=["Regions"])
app.include_router(layers.router,  prefix="/api/v1/layers",    tags=["Layers"])
app.include_router(zones.router,   prefix="/api/v1/zones",     tags=["Zones"])
app.include_router(alerts.router,  prefix="/api/v1/alerts",    tags=["Alerts"])
app.include_router(imports.router, prefix="/api/v1/imports",   tags=["Imports"])
app.include_router(reports.router, prefix="/api/v1/reports",   tags=["Reports"])
app.include_router(users.router,   prefix="/api/v1/users",     tags=["Users"])
app.include_router(system.router,  prefix="/api/v1/system",    tags=["System"])
app.include_router(anomalies.router, prefix="/api/v1/anomalies", tags=["Anomalies"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["Risk"])
app.include_router(ws.router,                                  tags=["WebSocket"])
app.include_router(geocode.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "raphael-api"}

# Mount the built frontend dist as StaticFiles
import logging
import shutil
from fastapi.responses import FileResponse, Response

logger = logging.getLogger(__name__)

dist_path = os.environ.get(
    'RAPHAEL_FRONTEND_DIST',
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
        'raphael-frontend', 'dist', 'client'
    )
)

logger.info(f"Frontend dist path: {dist_path}, exists: {os.path.exists(dist_path)}")

if os.path.exists(dist_path):
    # Copy _shell.html to index.html if index.html is missing (required for TanStack Start SPA mode)
    shell_file = os.path.join(dist_path, "_shell.html")
    index_file = os.path.join(dist_path, "index.html")
    if os.path.exists(shell_file) and not os.path.exists(index_file):
        try:
            shutil.copyfile(shell_file, index_file)
            logger.info("Copied _shell.html to index.html successfully")
        except Exception as e:
            logger.error(f"Failed to copy _shell.html to index.html: {e}")

    # Mount assets folder
    assets_path = os.path.join(dist_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
        logger.info(f"Mounted assets directory: {assets_path}")
        
    # Catch-all route to serve index.html for client-side routing (SPA)
    @app.get("/{fallback_path:path}")
    async def serve_spa(fallback_path: str):
        # Ignore requests that look like files (e.g. styles.css) but weren't found in assets mount
        if "." in fallback_path and not fallback_path.endswith(".html"):
            return Response(status_code=404)
        
        if os.path.exists(index_file):
            return FileResponse(index_file)
        
        return Response(content='{"detail":"Not Found"}', media_type="application/json", status_code=404)
else:
    logger.warning(f"Frontend dist not found at: {dist_path} — API-only mode")

