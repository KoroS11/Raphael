# Stage 03 — FastAPI Local API

## Prerequisites
Stage 02 completed. Database is running and migrations are applied.

## Objective
Build the complete FastAPI local REST API that the frontend reads from exclusively. Every route defined in `docs/SYSTEM_ARCHITECTURE.md` Section 6.2 must be implemented.

---

## Step 1 — Create FastAPI Entry Point

Create `backend/api/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .routes import regions, layers, zones, alerts, imports, reports, users, system

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Raphael API starting...")
    yield
    # Shutdown
    print("Raphael API shutting down...")

app = FastAPI(
    title="Raphael Environmental Intelligence API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(regions.router, prefix="/api/v1/regions",   tags=["Regions"])
app.include_router(layers.router,  prefix="/api/v1/layers",    tags=["Layers"])
app.include_router(zones.router,   prefix="/api/v1/zones",     tags=["Zones"])
app.include_router(alerts.router,  prefix="/api/v1/alerts",    tags=["Alerts"])
app.include_router(imports.router, prefix="/api/v1/imports",   tags=["Imports"])
app.include_router(reports.router, prefix="/api/v1/reports",   tags=["Reports"])
app.include_router(users.router,   prefix="/api/v1/users",     tags=["Users"])
app.include_router(system.router,  prefix="/api/v1/system",    tags=["System"])

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "raphael-api"}
```

---

## Step 2 — Create Auth Middleware

Create `backend/api/auth.py`:

```python
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
