import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from db.connection import get_db
from db.models import User

SECRET_KEY   = os.getenv("RAPHAEL_SECRET_KEY", "change-me-in-production")
ALGORITHM    = "HS256"
TOKEN_EXPIRE = timedelta(hours=8)

security    = HTTPBearer()

def create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + TOKEN_EXPIRE
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
