import os
import structlog
from pathlib import Path
try:
    from prefect import flow, task
except ImportError:
    def task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def flow(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
from datetime import datetime, timezone

from db.connection import SessionLocal
from db.models import ReportJob
from reports.generator import generate_report_file

log = structlog.get_logger()

@task(name="Update Job Progress")
def update_job_status(job_id: str, status: str, progress_pct: int, current_step: str, file_path: str = None, file_size: int = None, page_count: int = None, error_message: str = None):
    db = SessionLocal()
    try:
        job = db.query(ReportJob).filter(ReportJob.id == job_id).first()
        if job:
            job.status = status
            job.progress_pct = progress_pct
            job.current_step = current_step
            if file_path:
                job.file_path = file_path
            if file_size is not None:
                job.file_size = file_size
            if page_count is not None:
                job.page_count = page_count
            if error_message:
                job.error_message = error_message
            db.commit()
    except Exception as e:
        log.error("update_job_status_failed", job_id=job_id, error=str(e))
    finally:
        db.close()

@flow(name="Generate Report Flow")
def generate_report_flow(job_id: str):
    log.info("Starting report generation flow", job_id=job_id)
    
    # 1. Start and Fetch Data step
    update_job_status(
        job_id=job_id,
        status="generating",
        progress_pct=10,
        current_step="Fetching zone data"
    )
    
    db = SessionLocal()
    try:
        job = db.query(ReportJob).filter(ReportJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job with ID {job_id} not found in DB.")
            
        # 2. Generating charts step
        update_job_status(
            job_id=job_id,
            status="generating",
            progress_pct=40,
            current_step="Generating charts"
        )
        
        # 3. Rendering PDF step
        update_job_status(
            job_id=job_id,
            status="generating",
            progress_pct=75,
            current_step="Rendering PDF"
        )
        
        # Core PDF Generation
        out_path = generate_report_file(db, job)
        
        # Measure file size
        file_size = out_path.stat().st_size if out_path.exists() else 0
        
        # Basic page count estimation (ReportLab / WeasyPrint outputs are parsed)
        page_count = 2 # default fallback
        try:
            # We can count '/Type /Page' in the PDF binary to get exact page count!
            with open(out_path, "rb") as f:
                content = f.read()
                page_count = max(1, content.count(b"/Type /Page") or content.count(b"/Page\n") or content.count(b"/Page ") or 2)
        except Exception:
            pass
            
        # 4. Completion step
        update_job_status(
            job_id=job_id,
            status="complete",
            progress_pct=100,
            current_step="Complete",
            file_path=str(out_path),
            file_size=file_size,
            page_count=page_count
        )
        log.info("Report generation flow complete", job_id=job_id, path=str(out_path))
        
    except Exception as e:
        log.error("report_generation_flow_failed", job_id=job_id, error=str(e))
        update_job_status(
            job_id=job_id,
            status="failed",
            progress_pct=0,
            current_step="Failed",
            error_message=str(e)
        )
    finally:
        db.close()
