import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class HansenFlow(BaseIngestionFlow):
    source_key = "hansen"
    layer_type  = "ndvi"

@flow(name="hansen-ingestion")
def ndvi_hansen_flow():
    print("[STUB] hansen ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")

if __name__ == "__main__":
    ndvi_hansen_flow()
