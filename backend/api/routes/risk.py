import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from db.connection import get_db

router = APIRouter()

@router.get("/propagation")
async def get_plume_propagation(region_id: str = Query(None), db: Session = Depends(get_db)):
    latest_run_time = db.execute(text("""
        SELECT MAX(computed_at) FROM ml_outputs
        WHERE model_type = 'gaussian_plume'
    """)).scalar()
    
    if not latest_run_time:
        return {
            "status": "success",
            "data": None,
            "meta": {"message": "No plume data found"},
            "errors": []
        }
        
    rows = db.execute(text("""
        SELECT value, explanation
        FROM ml_outputs
        WHERE model_type = 'gaussian_plume'
          AND computed_at = :latest_run
    """), {"latest_run": latest_run_time}).fetchall()
    
    if not rows:
        return {
            "status": "success",
            "data": None,
            "meta": {"message": "No plume rows found for the latest run"},
            "errors": []
        }
        
    first_expl = {}
    try:
        first_expl = json.loads(rows[0][1])
    except Exception:
        pass
        
    stability_class = first_expl.get("pg_stability", "D")
    wind_speed = first_expl.get("wind_speed_ms", 9.4)
    source_station = first_expl.get("source_station", "Unknown")
    
    pg_labels = {
        "A": "Extremely Unstable",
        "B": "Moderately Unstable",
        "C": "Slightly Unstable",
        "D": "Neutral",
        "E": "Slightly Stable",
        "F": "Moderately Stable"
    }
    stability_label = pg_labels.get(stability_class, "Neutral")
    
    profiles = []
    for r in rows:
        try:
            expl = json.loads(r[1])
        except Exception:
            continue
            
        profiles.append({
            "distance_km": expl.get("distance_km", 0.0),
            "peak_concentration": r[0],
            "sigma_y": expl.get("sigma_y_m", 0.0) / 1000.0,
            "sigma_z": expl.get("sigma_z_m", 0.0) / 1000.0
        })
        
    profiles.sort(key=lambda p: p["distance_km"])
    
    return {
        "status": "success",
        "data": {
            "stability_class": stability_class,
            "stability_label": stability_label,
            "wind_speed": wind_speed,
            "source_station": source_station,
            "profiles": profiles
        },
        "meta": {"computed_at": latest_run_time.isoformat() if hasattr(latest_run_time, "isoformat") else str(latest_run_time)},
        "errors": []
    }
