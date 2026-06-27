from pydantic import BaseModel
from typing import Any, Optional, List
from datetime import datetime

class Meta(BaseModel):
    timestamp:   datetime = datetime.utcnow()
    last_synced: Optional[datetime] = None
    source:      Optional[str]      = None
    count:       Optional[int]      = None
    model_version: Optional[str]    = None

class APIResponse(BaseModel):
    status: str = "success"
    data:   Any = None
    meta:   Meta = Meta()
    errors: List[dict] = []

class ErrorResponse(BaseModel):
    status: str = "error"
    data:   None = None
    meta:   Meta = Meta()
    errors: List[dict] = []
