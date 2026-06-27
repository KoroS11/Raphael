import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class OverpassFlow(BaseIngestionFlow):
    source_key = "overpass"
    layer_type  = "urban"

@flow(name="overpass-ingestion")
def osm_features_flow():
    print("[STUB] overpass ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")

if __name__ == "__main__":
    osm_features_flow()
