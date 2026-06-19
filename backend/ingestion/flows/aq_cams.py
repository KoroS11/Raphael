import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class CopernicusCAMSFlow(BaseIngestionFlow):
    source_key = "copernicus_cams"
    layer_type  = "aq"

@flow(name="copernicus_cams-ingestion")
def aq_cams_flow():
    print("[STUB] copernicus_cams ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")
