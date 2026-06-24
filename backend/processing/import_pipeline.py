import os
import uuid
import pandas as pd
import geopandas as gpd
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from db.models import Source, RawObservation, Region, ImportDataset

class ImportPipeline:
    def __init__(self, db: Session):
        self.db = db

