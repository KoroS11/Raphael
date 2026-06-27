import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class FEMAFloodFlow(BaseIngestionFlow):
    source_key = "fema_flood"
    layer_type  = "hazard"

@flow(name="fema_flood-ingestion")
def hazard_fema_flow():
    print("[STUB] fema_flood ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")

if __name__ == "__main__":
    hazard_fema_flow()
