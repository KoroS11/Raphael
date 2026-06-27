import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class NASASedacFlow(BaseIngestionFlow):
    source_key = "nasa_sedac"
    layer_type  = "socioeconomic"

@flow(name="nasa_sedac-ingestion")
def sedac_socioeco_flow():
    print("[STUB] nasa_sedac ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")

if __name__ == "__main__":
    sedac_socioeco_flow()
