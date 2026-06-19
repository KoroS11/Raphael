import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db.connection import get_db
from api.auth import get_current_user
from processing.import_pipeline import ImportPipeline
from db.models import ImportDataset

router = APIRouter()

PENDING_DIR = "data/imports/pending"
os.makedirs(PENDING_DIR, exist_ok=True)

class ValidatePayload(BaseModel):
    path: str
    format: str
    mapping: dict

class IngestPayload(BaseModel):
    path: str
    format: str
    mapping: dict
    dataset_name: str
    layer_type: str
    region_id: str = None

@router.get("/")
@router.get("/datasets")
async def list_imports(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    datasets = db.query(ImportDataset).filter(ImportDataset.is_visible == True).order_by(ImportDataset.imported_at.desc()).all()
    data = []
    for d in datasets:
        data.append({
            "id": str(d.id),
            "name": d.name,
            "format": d.format,
            "row_count": d.row_count,
            "schema_map": d.schema_map,
            "layer_type": d.layer_type,
            "imported_at": d.imported_at.isoformat() if d.imported_at else None
        })
    return {
        "status": "success",
        "data": data,
        "meta": {"count": len(data)},
        "errors": []
    }

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    pipeline = ImportPipeline(db)
    fmt = pipeline.detect_format(file.filename)
    if fmt == 'unknown':
        raise HTTPException(status_code=400, detail="Unsupported file format.")
    
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    pending_path = os.path.join(PENDING_DIR, f"{file_id}{ext}")
    
    try:
        with open(pending_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
        
    try:
        df = pipeline.load_file(pending_path, fmt)
    except Exception as e:
        if os.path.exists(pending_path):
            os.remove(pending_path)
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")
        
    mapping = pipeline.detect_column_mapping(df)
    
    # Clean NaN values for JSON serialization
    df_preview = df.head(10).fillna("")
    preview = df_preview.to_dict(orient="records")
    columns = list(df.columns)
    
    return {
        "status": "success",
        "data": {
            "file_id": file_id,
            "filename": file.filename,
            "format": fmt,
            "path": pending_path,
            "columns": columns,
            "suggested_mapping": mapping,
            "preview": preview
        }
    }

@router.post("/validate")
async def validate_file(
    payload: ValidatePayload,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    pipeline = ImportPipeline(db)
    if not os.path.exists(payload.path):
        raise HTTPException(status_code=404, detail="Uploaded file not found.")
        
    try:
        df = pipeline.load_file(payload.path, payload.format)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to reload file: {e}")
        
    result = pipeline.validate(df, payload.mapping)
    return {
        "status": "success",
        "data": result
    }

@router.post("/ingest")
async def ingest_file(
    payload: IngestPayload,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    pipeline = ImportPipeline(db)
    if not os.path.exists(payload.path):
        raise HTTPException(status_code=404, detail="Uploaded file not found.")
    
    try:
        df = pipeline.load_file(payload.path, payload.format)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load file for ingestion: {e}")
        
    val_res = pipeline.validate(df, payload.mapping)
    if val_res["valid_rows"] == 0:
        raise HTTPException(status_code=400, detail="No valid rows found to ingest based on mapping.")
        
    res = pipeline.ingest(
        df=df,
        mapping=payload.mapping,
        dataset_name=payload.dataset_name,
        layer_type=payload.layer_type,
        user_id=current_user.id,
        region_id=payload.region_id
    )
    
    if os.path.exists(payload.path):
        try:
            os.remove(payload.path)
        except Exception:
            pass
            
    from api.routes.ws import broadcast
    from datetime import datetime, timezone
    event = {
        "type": "sync_status",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "source": "custom_import",
            "layer_type": payload.layer_type,
            "count": res["ingested"],
            "status": "success"
        }
    }
    # run async broadcast
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(broadcast(event))
        else:
            loop.run_until_complete(broadcast(event))
    except Exception:
        # Fallback if event loop handling fails
        pass
        
    return {
        "status": "success",
        "data": res
    }

@router.delete("/{id}")
@router.delete("/datasets/{id}")
async def delete_import(id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    dataset = db.query(ImportDataset).filter(ImportDataset.id == id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    db.delete(dataset)
    db.commit()
    return {
        "status": "success",
        "data": {"id": id, "deleted": True},
        "meta": {},
        "errors": []
    }
