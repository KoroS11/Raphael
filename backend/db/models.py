import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, DateTime, Date, Integer, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import declarative_base, relationship
from geoalchemy2 import Geometry

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username           = Column(String(100), unique=True, nullable=False)
    password_hash      = Column(Text, nullable=False)
    display_name       = Column(String(200))
    role               = Column(String(20), nullable=False, default="viewer")
    organization       = Column(String(200))
    preferred_language = Column(String(5), default="en")
    created_at         = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_active_at     = Column(DateTime(timezone=True))

class ActivityLog(Base):
    __tablename__ = "activity_log"
