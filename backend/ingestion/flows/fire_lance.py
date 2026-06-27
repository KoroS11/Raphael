import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class NASALanceFlow(BaseIngestionFlow):
    source_key = "nasa_lance"
    layer_type  = "fire"

@flow(name="nasa_lance-ingestion")
def fire_lance_flow():
    print("[STUB] nasa_lance ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")

if __name__ == "__main__":
    fire_lance_flow()
