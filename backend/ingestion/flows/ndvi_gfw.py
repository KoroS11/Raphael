import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class GFWFlow(BaseIngestionFlow):
    source_key = "gfw"
    layer_type  = "ndvi"

@flow(name="gfw-ingestion")
def ndvi_gfw_flow():
    print("[STUB] gfw ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")

if __name__ == "__main__":
    ndvi_gfw_flow()
