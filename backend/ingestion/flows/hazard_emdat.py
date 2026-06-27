import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class EMDATFlow(BaseIngestionFlow):
    source_key = "emdat"
    layer_type  = "hazard"

@flow(name="emdat-ingestion")
def hazard_emdat_flow():
    print("[STUB] emdat ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")

if __name__ == "__main__":
    hazard_emdat_flow()
