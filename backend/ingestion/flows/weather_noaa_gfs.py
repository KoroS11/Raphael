import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class NOAAGFSFlow(BaseIngestionFlow):
    source_key = "noaa_gfs"
    layer_type  = "weather"

@flow(name="noaa_gfs-ingestion")
def weather_noaa_gfs_flow():
    print("[STUB] noaa_gfs ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")

if __name__ == "__main__":
    weather_noaa_gfs_flow()
