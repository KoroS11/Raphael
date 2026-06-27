from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from db.connection import get_db
from api.auth import get_current_user
from db.models import ReportJob, ZoneGeometry
from reports.flow import generate_report_flow
import uuid
import os
from datetime import datetime, timezone

router = APIRouter()

@router.post("/generate")
async def generate_report(payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    report_type = payload.get("type", "zone")
    org_name = payload.get("organization", "Delhi Environmental Protection")
    
    # Handle both zone_id (for backwards compatibility) and zone_ids (comparison report)
    zone_ids = []
    if "zone_ids" in payload:
        zone_ids = payload.get("zone_ids", [])
    elif "zone_id" in payload:
        zone_id = payload.get("zone_id")
        if zone_id and zone_id != "00000000-0000-0000-0000-000000000000":
            zone_ids = [zone_id]
            
    # Default date range if not specified (last 7 days)
    date_range = payload.get("date_range", {})
    if not date_range or not date_range.get("start") or not date_range.get("end"):
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=7)
        date_range = {
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "indicator": payload.get("indicator", "aq")
        }
    else:
        # ensure indicator is set if it's trends report
        if "indicator" not in date_range and "indicator" in payload:
            date_range["indicator"] = payload.get("indicator")
            
    job_id = str(uuid.uuid4())
    
    job = ReportJob(
        id=uuid.UUID(job_id),
        report_type=report_type,
        zone_ids=zone_ids,
        date_range=date_range,
        status="queued",
        current_step="Queued in task manager",
        progress_pct=0,
        requested_by=current_user.id
    )
    db.add(job)
    db.commit()
    
    # Spawn the Prefect task flow asynchronously
    background_tasks.add_task(generate_report_flow, job_id)
    
    return {
        "status": "success",
        "data": {
            "job_id": job_id,
            "estimated_seconds": 15
        },
        "meta": {},
        "errors": []
    }

@router.get("")
@router.get("/")
async def list_reports(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    jobs = db.query(ReportJob).filter(ReportJob.requested_by == current_user.id).order_by(ReportJob.generated_at.desc()).all()
    data = []
    for j in jobs:
        # Resolve zone names
        zone_names = []
        if j.zone_ids:
            for zid in j.zone_ids:
                z = db.query(ZoneGeometry.name).filter(ZoneGeometry.id == zid).scalar()
                if z:
                    zone_names.append(z)
        zone_str = ", ".join(zone_names) if zone_names else "Delhi NCT Aggregate"
        
        data.append({
            "id": str(j.id),
            "report_type": j.report_type,
            "zone_names": zone_str,
            "date_range": j.date_range,
            "status": j.status,
            "file_size": j.file_size,
            "page_count": j.page_count,
            "generated_at": j.generated_at.isoformat() if j.generated_at else None,
            "error_message": j.error_message
        })
    return {
        "status": "success",
        "data": data,
        "meta": {"count": len(data)},
        "errors": []
    }

@router.get("/{job_id}/status")
async def get_report_status(job_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    job = db.query(ReportJob).filter(ReportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Report job not found.")
        
    # Simple estimate: if queued, 15s. if generating, 8s.
    est_sec = 0
    if job.status == "queued":
        est_sec = 15
    elif job.status == "generating":
        est_sec = 8
        
    return {
        "status": "success",
        "data": {
            "job_id": str(job.id),
            "status": job.status,
            "progress_pct": job.progress_pct,
            "current_step": job.current_step or "Processing",
            "estimated_seconds_remaining": est_sec,
            "file_size_bytes": job.file_size,
            "created_at": job.generated_at.isoformat() if job.generated_at else None,
            "error_message": job.error_message
        },
        "meta": {},
        "errors": []
    }

@router.get("/{job_id}/download")
async def download_report(job_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    job = db.query(ReportJob).filter(ReportJob.id == job_id).first()
    if not job or not job.file_path:
        raise HTTPException(status_code=404, detail="Report PDF not found.")
        
    if not os.path.exists(job.file_path):
        raise HTTPException(status_code=404, detail="PDF file does not exist on disk.")
        
    filename = os.path.basename(job.file_path)
    return FileResponse(
        path=job.file_path,
        filename=filename,
        media_type="application/pdf"
    )

@router.delete("/{job_id}")
async def delete_report(job_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    job = db.query(ReportJob).filter(ReportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Report job not found.")
        
    # Delete file from disk
    if job.file_path and os.path.exists(job.file_path):
        try:
            os.remove(job.file_path)
        except Exception:
            pass
            
    db.delete(job)
    db.commit()
    
    return {
        "status": "success",
        "data": {"id": job_id, "deleted": True},
        "meta": {},
        "errors": []
    }
