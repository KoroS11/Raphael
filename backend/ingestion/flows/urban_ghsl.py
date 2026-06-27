import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class GHSLFlow(BaseIngestionFlow):
    source_key = "ghsl"
    layer_type  = "urban"

@flow(name="ghsl-ingestion")
def urban_ghsl_flow():
    print("[STUB] ghsl ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")

if __name__ == "__main__":
    urban_ghsl_flow()
