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
from db.connection import get_db
from db.models import User

SECRET_KEY   = os.getenv("RAPHAEL_SECRET_KEY", "change-me-in-production")
ALGORITHM    = "HS256"
TOKEN_EXPIRE = timedelta(hours=8)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security    = HTTPBearer()

def create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + TOKEN_EXPIRE
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_role(*roles: str):
    async def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return checker
```

---

## Step 3 — Create Pydantic Response Models

Create `backend/api/models/responses.py`:

```python
from pydantic import BaseModel
from typing import Any, Optional, List
from datetime import datetime

class Meta(BaseModel):
    timestamp:   datetime = datetime.utcnow()
    last_synced: Optional[datetime] = None
    source:      Optional[str]      = None
    count:       Optional[int]      = None
    model_version: Optional[str]    = None

class APIResponse(BaseModel):
    status: str = "success"
    data:   Any = None
    meta:   Meta = Meta()
    errors: List[dict] = []

class ErrorResponse(BaseModel):
    status: str = "error"
    data:   None = None
    meta:   Meta = Meta()
