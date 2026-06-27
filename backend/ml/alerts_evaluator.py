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
        if isinstance(obs_time, str):
            try:
                obs_time = datetime.fromisoformat(obs_time.replace('Z', '+00:00'))
            except Exception:
                obs_time = datetime.now(timezone.utc)
        return float(res[0]), obs_time
    return None, None

def get_previous_zone_value(db: Session, zone_id: str, layer_type: str) -> tuple:
    # Returns (prev_value, timestamp) or (None, None)
    if layer_type in ["risk_score", "composite"]:
        latest_risk = db.query(MLOutput).filter(
            MLOutput.zone_id == zone_id,
            MLOutput.model_type == "risk_score"
        ).order_by(MLOutput.computed_at.desc()).offset(1).limit(1).first()
        if latest_risk:
            return float(latest_risk.value), latest_risk.computed_at
        return None, None

    sql = text("""
        SELECT o.value, o.observed_at
        FROM raw_observations o
        JOIN zone_geometries z ON ST_Within(o.geometry, z.geometry)
        WHERE z.id = :zone_id
          AND o.layer_type = :layer_type
        ORDER BY o.observed_at DESC
        LIMIT 1 OFFSET 1
    """)
    res = db.execute(sql, {"zone_id": zone_id, "layer_type": layer_type}).fetchone()
    if res:
        obs_time = res[1]
        if isinstance(obs_time, str):
            try:
                obs_time = datetime.fromisoformat(obs_time.replace('Z', '+00:00'))
            except Exception:
                obs_time = datetime.now(timezone.utc)
        return float(res[0]), obs_time
    return None, None

def get_latest_attribution_cause(db: Session, zone_id: str) -> str:
    sql = text("""
        SELECT o.raw_payload
        FROM raw_observations o
        JOIN zone_geometries z ON ST_Within(o.geometry, z.geometry)
        WHERE z.id = :zone_id
          AND o.is_anomalous = 1
          AND o.observed_at >= datetime('now', '-24 hours')
        ORDER BY o.observed_at DESC
        LIMIT 1
    """)
    res = db.execute(sql, {"zone_id": zone_id}).fetchone()
    if res and res[0]:
        try:
            payload = json.loads(res[0]) if isinstance(res[0], str) else res[0]
            if payload and "cause" in payload:
                return str(payload["cause"])
        except Exception:
            pass
    return "environmental_factors"

def evaluate_alerts(db: Session, region_id: str):
    log.info("Starting rule-based alerts evaluation cycle", region_id=region_id)
    
    # 1. Ensure table columns exist
    ensure_columns(db)
    
    # 2. Get active rules
    rules = db.query(AlertRule).filter(AlertRule.is_active == True).all()
    if not rules:
        log.info("No active alert rules to evaluate")
        return
        
    # 3. Get all zones in region
    zones = db.query(ZoneGeometry).filter(ZoneGeometry.region_id == region_id).all()
    if not zones:
        log.warning("No zones found for active region to evaluate alerts", region_id=region_id)
        return

    for rule in rules:
        target_zones = []
        if rule.zone_id:
            # Check if this zone is in our active region
            zone = next((z for z in zones if str(z.id) == str(rule.zone_id)), None)
            if zone:
                target_zones.append(zone)
        else:
            target_zones = zones
            
        # Get all zone values for this layer in ONE query
        if rule.layer_type in ["risk_score", "composite"]:
            zone_values = db.execute(text("""
                SELECT zone_id, value
                FROM ml_outputs
                WHERE model_type = 'risk_score'
