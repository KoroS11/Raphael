from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from db.connection import get_db
from api.auth import get_current_user
from db.models import AlertRule, AlertEvent, ZoneGeometry
from datetime import datetime, timezone
import uuid

router = APIRouter()

@router.get("/rules")
async def list_rules(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    rules = db.query(AlertRule).filter(AlertRule.user_id == current_user.id).all()
    data = []
    for r in rules:
        zone = db.query(ZoneGeometry).filter(ZoneGeometry.id == r.zone_id).first() if r.zone_id else None
        data.append({
            "id": str(r.id),
            "name": r.name,
            "layer_type": r.layer_type,
            "zone_id": str(r.zone_id) if r.zone_id else "00000000-0000-0000-0000-000000000000",
            "zone_name": zone.name if zone else "Delhi NCT",
            "operator": r.operator,
            "threshold": r.threshold,
            "severity": r.severity,
            "time_window": r.time_window if r.time_window else "anytime",
            "is_active": r.is_active,
            "consecutive_fires": getattr(r, "consecutive_fires", 0)
        })
    return {
        "status": "success",
        "data": data,
        "meta": {"count": len(data)},
        "errors": []
    }

@router.post("/rules")
async def create_rule(payload: dict, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    operator = payload.get("operator", "gt")
    # Normalize operator to match DB constraint check
    if operator in [">", ">="]:
        operator = "gt"
    elif operator in ["<", "<="]:
        operator = "lt"
    
    zone_id = payload.get("zone_id")
    if zone_id == "00000000-0000-0000-0000-000000000000":
        zone_id = None

    rule = AlertRule(
        id=uuid.uuid4(),
        user_id=current_user.id,
        name=payload.get("name", "Alert Rule"),
        layer_type=payload.get("layer_type", "aq"),
        operator=operator,
        threshold=float(payload.get("threshold", 100)),
        severity=payload.get("severity", "warning"),
        zone_id=zone_id,
        time_window=payload.get("time_window", "anytime"),
        is_active=payload.get("is_active", True),
        consecutive_fires=0
    )
    db.add(rule)
    db.commit()
    
    # Return mapping matching frontend representation
    zone = db.query(ZoneGeometry).filter(ZoneGeometry.id == zone_id).first() if zone_id else None
    return {
        "status": "success",
        "data": {
            "id": str(rule.id),
            "name": rule.name,
            "layer_type": rule.layer_type,
            "zone_id": str(rule.zone_id) if rule.zone_id else "00000000-0000-0000-0000-000000000000",
            "zone_name": zone.name if zone else "Delhi NCT",
            "operator": rule.operator,
            "threshold": rule.threshold,
            "severity": rule.severity,
            "time_window": rule.time_window,
            "is_active": rule.is_active
        },
        "meta": {},
        "errors": []
    }

@router.put("/rules/{id}")
async def update_rule(id: str, payload: dict, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    rule = db.query(AlertRule).filter(AlertRule.id == id, AlertRule.user_id == current_user.id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found.")
        
    operator = payload.get("operator", rule.operator)
    if operator in [">", ">="]:
        operator = "gt"
    elif operator in ["<", "<="]:
        operator = "lt"
        
    zone_id = payload.get("zone_id", str(rule.zone_id) if rule.zone_id else None)
    if zone_id == "00000000-0000-0000-0000-000000000000":
        zone_id = None
        
    rule.name = payload.get("name", rule.name)
    rule.layer_type = payload.get("layer_type", rule.layer_type)
    rule.operator = operator
    rule.threshold = float(payload.get("threshold", rule.threshold))
    rule.severity = payload.get("severity", rule.severity)
    rule.zone_id = zone_id
    rule.time_window = payload.get("time_window", rule.time_window)
    rule.is_active = payload.get("is_active", rule.is_active)
    
    db.commit()
    return {
        "status": "success",
        "data": {"id": id},
        "meta": {},
        "errors": []
    }

@router.delete("/rules/{id}")
async def delete_rule(id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    rule = db.query(AlertRule).filter(AlertRule.id == id, AlertRule.user_id == current_user.id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found.")
    db.delete(rule)
    db.commit()
    return {
        "status": "success",
        "data": {"id": id, "deleted": True},
        "meta": {},
        "errors": []
    }

@router.get("/events")
async def list_events(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    events = db.query(AlertEvent).order_by(AlertEvent.triggered_at.desc()).all()
    data = []
    for e in events:
        rule = db.query(AlertRule).filter(AlertRule.id == e.rule_id).first()
        # Find zone name by looking up the zone geometries containing event location
        zone_name = "Delhi NCT"
        if rule and rule.zone_id:
            zone = db.query(ZoneGeometry).filter(ZoneGeometry.id == rule.zone_id).first()
            if zone:
                zone_name = zone.name
        else:
            # Query zone geometries matching event centroid location
            sql = text("""
                SELECT z.name FROM zone_geometries z
                WHERE ST_Within(:location, z.geometry)
                LIMIT 1
            """)
            res = db.execute(sql, {"location": e.location}).fetchone() if e.location else None
            if res:
                zone_name = res[0]
                
        data.append({
            "id": str(e.id),
            "rule_id": str(e.rule_id),
            "rule_name": rule.name if rule else "Alert Fired",
            "layer_type": rule.layer_type if rule else "env",
            "observed_value": e.observed_value,
            "triggered_at": e.triggered_at.isoformat() if e.triggered_at else None,
            "acknowledged": e.acknowledged,
            "acknowledged_at": e.acknowledged_at.isoformat() if e.acknowledged_at else None,
            "zone_name": zone_name,
            "severity": getattr(e, "severity", rule.severity if rule else "warning"),
            "unit": "ug/m3" if (rule and rule.layer_type == "aq") else "°C" if (rule and rule.layer_type == "lst") else ""
        })
    return {
        "status": "success",
        "data": data,
        "meta": {"count": len(data)},
        "errors": []
    }

@router.post("/events/{id}/acknowledge")
@router.post("/{id}/acknowledge")
async def acknowledge_event(id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    event = db.query(AlertEvent).filter(AlertEvent.id == id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Alert event not found.")
        
    event.acknowledged = True
    event.acknowledged_at = datetime.now(timezone.utc)
    event.acknowledged_by = current_user.id
    
    # Reset consecutive fire counter on the rule
    rule = db.query(AlertRule).filter(AlertRule.id == event.rule_id).first()
    if rule:
        setattr(rule, "consecutive_fires", 0)
        
    db.commit()
    return {
        "status": "success",
        "data": {"id": id, "acknowledged": True},
        "meta": {},
        "errors": []
    }
