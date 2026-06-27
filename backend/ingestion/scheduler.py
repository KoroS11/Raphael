import sys
import os
from datetime import timedelta

# Ensure backend directory is in the path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from prefect import serve
from ingestion.flows.aq_openaq         import openaq_flow
from ingestion.flows.aq_waqi           import waqi_flow
from ingestion.flows.aq_iqair          import iqair_flow
from ingestion.flows.weather_openmeteo import openmeteo_flow
from ingestion.flows.fire_firms        import firms_flow
from ingestion.flows.boundaries_gadm   import gadm_flow
from ingestion.flows.hazard_gdacs      import gdacs_flow
from ingestion.flows.lst_modis         import lst_modis_flow
from prefect.client.schemas.schedules  import IntervalSchedule

if __name__ == "__main__":
    serve(
        openaq_flow.to_deployment(
            name="openaq-hourly",
            schedule=IntervalSchedule(interval=timedelta(hours=1))
        ),
        waqi_flow.to_deployment(
            name="waqi-hourly",
            schedule=IntervalSchedule(interval=timedelta(hours=1))
        ),
        iqair_flow.to_deployment(
            name="iqair-hourly",
            schedule=IntervalSchedule(interval=timedelta(hours=1))
        ),
        openmeteo_flow.to_deployment(
            name="openmeteo-hourly",
            schedule=IntervalSchedule(interval=timedelta(hours=1))
        ),
        firms_flow.to_deployment(
            name="firms-3hourly",
            schedule=IntervalSchedule(interval=timedelta(hours=3))
        ),
        gdacs_flow.to_deployment(
            name="gdacs-hourly",
            schedule=IntervalSchedule(interval=timedelta(hours=1))
        ),
        lst_modis_flow.to_deployment(
            name="modis-lst-daily",
            schedule=IntervalSchedule(interval=timedelta(hours=24))
        ),
    )
