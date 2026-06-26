import os
import uuid
import json
import structlog
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session
from db.models import AlertRule, AlertEvent, ZoneGeometry, MLOutput, RawObservation
from ml.runner import broadcast_sync, _recommend_action

log = structlog.get_logger()

def ensure_columns(db: Session):
    dialect = db.bind.dialect.name
    # 1. Check consecutive_fires on alert_rules
    try:
        db.execute(text("SELECT consecutive_fires FROM alert_rules LIMIT 1"))
    except Exception:
        db.rollback()
        log.info("Adding consecutive_fires column to alert_rules")
        if dialect == "postgresql":
            db.execute(text("ALTER TABLE alert_rules ADD COLUMN consecutive_fires INT DEFAULT 0;"))
        else:
            db.execute(text("ALTER TABLE alert_rules ADD COLUMN consecutive_fires INTEGER DEFAULT 0;"))
        db.commit()
    
    # 2. Check severity on alert_events
    try:
        db.execute(text("SELECT severity FROM alert_events LIMIT 1"))
    except Exception:
        db.rollback()
        log.info("Adding severity column to alert_events")
        if dialect == "postgresql":
            db.execute(text("ALTER TABLE alert_events ADD COLUMN severity VARCHAR(20) DEFAULT 'warning';"))
        else:
            db.execute(text("ALTER TABLE alert_events ADD COLUMN severity TEXT DEFAULT 'warning';"))
        db.commit()

def get_current_zone_value(db: Session, zone_id: str, layer_type: str) -> tuple:
    # Returns (current_value, timestamp) or (None, None)
    if layer_type in ["risk_score", "composite"]:
        latest_risk = db.query(MLOutput).filter(
            MLOutput.zone_id == zone_id,
            MLOutput.model_type == "risk_score"
        ).order_by(MLOutput.computed_at.desc()).first()
        if latest_risk:
            return float(latest_risk.value), latest_risk.computed_at
        return None, None

    # Query latest raw observation inside zone geometry
    sql = text("""
        SELECT o.value, o.observed_at
        FROM raw_observations o
        JOIN zone_geometries z ON ST_Within(o.geometry, z.geometry)
        WHERE z.id = :zone_id
          AND o.layer_type = :layer_type
        ORDER BY o.observed_at DESC
        LIMIT 1
    """)
    res = db.execute(sql, {"zone_id": zone_id, "layer_type": layer_type}).fetchone()
    if res:
        # Convert str timestamp to datetime if SQLite returning string
        obs_time = res[1]
