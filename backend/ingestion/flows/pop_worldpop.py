import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class WorldPopFlow(BaseIngestionFlow):
    source_key = "worldpop"
    layer_type  = "population"

@flow(name="worldpop-ingestion")
def pop_worldpop_flow():
    print("[STUB] worldpop ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")

if __name__ == "__main__":
    pop_worldpop_flow()
