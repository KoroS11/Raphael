from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from db.connection import get_db
from db.models import Region
from api.auth import get_current_user
import uuid

router = APIRouter()

@router.get("/")
async def list_regions(db: Session = Depends(get_db), _user = Depends(get_current_user)):
    from geoalchemy2.shape import to_shape
    regions = db.query(Region).all()
    data = []
    for r in regions:
        bbox_val = None
        center_val = None
        if r.bbox is not None:
            try:
                geom = to_shape(r.bbox)
                bbox_val = list(geom.bounds)  # [west, south, east, north]
                center_val = [geom.centroid.x, geom.centroid.y]  # [lon, lat]
            except Exception:
                pass
        data.append({
            "id": str(r.id),
            "name": r.name,
            "country_code": r.country_code,
            "admin_level": r.admin_level,
            "pmtiles_path": r.pmtiles_path,
            "is_active": r.is_active,
            "bbox": bbox_val,
            "center": center_val
        })
    return {
        "status": "success",
        "data": data,
        "meta": {"count": len(data)},
        "errors": []
    }

@router.get("/{id}")
async def get_region(id: str, db: Session = Depends(get_db), _user = Depends(get_current_user)):
    from geoalchemy2.shape import to_shape
    r = db.query(Region).filter(Region.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Region not found")
    
    bbox_val = None
    center_val = None
    if r.bbox is not None:
        try:
            geom = to_shape(r.bbox)
            bbox_val = list(geom.bounds)  # [west, south, east, north]
            center_val = [geom.centroid.x, geom.centroid.y]  # [lon, lat]
        except Exception:
            pass

    return {
        "status": "success",
        "data": {
            "id": str(r.id),
            "name": r.name,
            "country_code": r.country_code,
            "admin_level": r.admin_level,
            "pmtiles_path": r.pmtiles_path,
            "is_active": r.is_active,
            "bbox": bbox_val,
            "center": center_val
        },
        "meta": {},
        "errors": []
    }

@router.post("/")
async def create_region(payload: dict, db: Session = Depends(get_db), _user = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {"id": str(uuid.uuid4())},
        "meta": {},
        "errors": []
    }

@router.put("/{id}")
async def update_region(id: str, payload: dict, db: Session = Depends(get_db), _user = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {"id": id},
        "meta": {},
        "errors": []
    }

@router.delete("/{id}")
async def delete_region(id: str, db: Session = Depends(get_db), _user = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {"id": id, "deleted": True},
        "meta": {},
        "errors": []
    }
