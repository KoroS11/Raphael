import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prefect import flow
from ingestion.base import BaseIngestionFlow

class OpenWeatherMapFlow(BaseIngestionFlow):
    source_key = "openweathermap"
    layer_type  = "weather"

@flow(name="openweathermap-ingestion")
def weather_openweathermap_flow():
    print("[STUB] openweathermap ingestion not yet implemented")
    print("Will be completed in Stage 05 (raster flows) or Stage 09")

if __name__ == "__main__":
    weather_openweathermap_flow()
