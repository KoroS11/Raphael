import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class NOAANCEIFlow(BaseIngestionFlow):
    source_key = "noaa_ncei"
    layer_type  = "hazard"

@flow(name="noaa_ncei-ingestion")
def hazard_noaa_ncei_flow():
    print("[STUB] noaa_ncei ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")

if __name__ == "__main__":
    hazard_noaa_ncei_flow()
