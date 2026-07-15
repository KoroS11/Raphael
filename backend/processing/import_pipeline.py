"""
Raphael — Custom Data Import Pipeline

Loads, validates, and ingests environmental datasets (CSV, Excel, GeoJSON, KML, Shapefile).
Supports dynamic column mapping, coordinate normalization, and database storage.
"""
import os
import uuid
import pandas as pd
import geopandas as gpd
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.models import Source, RawObservation, Region, ImportDataset
from shapely.geometry import Point

class ImportPipeline:
    def __init__(self, db: Session):
        self.db = db

    def detect_format(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        mapping = {
            ".csv": "csv",
            ".geojson": "geojson",
            ".kml": "kml",
            ".shp": "shapefile",
            ".xlsx": "excel",
            ".xls": "excel"
        }
        return mapping.get(ext, "unknown")

    def load_file(self, path: str, fmt: str) -> pd.DataFrame:
        if fmt == "csv":
            return pd.read_csv(path)
        elif fmt == "excel":
            return pd.read_excel(path)
        elif fmt in ("geojson", "shapefile", "kml"):
            # If shapefile or kml is in a zip or folder, geopandas handles it natively
            gdf = gpd.read_file(path)
            # Convert geometry to lon/lat columns for preview/mapping if needed
            if "geometry" in gdf.columns:
                # Reproject to EPSG:4326 if not already
                if gdf.crs and gdf.crs.to_epsg() != 4326:
                    gdf = gdf.to_crs(epsg=4326)
                # Extract lat/lon from point geometry
                gdf["longitude"] = gdf.geometry.x
                gdf["latitude"] = gdf.geometry.y
            return pd.DataFrame(gdf)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def detect_column_mapping(self, df: pd.DataFrame) -> dict:
        mapping = {}
        cols = [c.lower() for c in df.columns]
        
        # Latitude
        for idx, col in enumerate(cols):
            if col in ("lat", "latitude", "y", "lat_deg"):
                mapping["latitude"] = df.columns[idx]
                break

        # Longitude
        for idx, col in enumerate(cols):
            if col in ("lon", "longitude", "x", "lon_deg", "lng"):
                mapping["longitude"] = df.columns[idx]
                break

        # Value
        for idx, col in enumerate(cols):
            if col in ("val", "value", "pm25", "pm2.5", "aqi", "temp", "temperature", "ndvi"):
                mapping["value"] = df.columns[idx]
                break

        # Observed at / Timestamp
        for idx, col in enumerate(cols):
            if col in ("date", "time", "timestamp", "observed_at", "datetime", "utc"):
                mapping["observed_at"] = df.columns[idx]
                break

        # Station ID
        for idx, col in enumerate(cols):
            if col in ("station_id", "station", "id"):
                mapping["station_id"] = df.columns[idx]
                break

        # Station Name
        for idx, col in enumerate(cols):
            if col in ("station_name", "name"):
                mapping["station_name"] = df.columns[idx]
                break

        # Unit
        for idx, col in enumerate(cols):
            if col in ("unit", "units"):
                mapping["unit"] = df.columns[idx]
                break

        return mapping

    def validate(self, df: pd.DataFrame, mapping: dict) -> dict:
        errors = []
        valid_count = 0
        invalid_count = 0

        # Required columns for basic observation
        lat_col = mapping.get("latitude")
        lon_col = mapping.get("longitude")
        val_col = mapping.get("value")

        if not lat_col or not lon_col or not val_col:
            return {
                "valid_rows": 0,
                "invalid_rows": len(df),
                "errors": [{"row": 0, "message": "Missing required coordinate or value mapping."}]
            }

        for idx, row in df.iterrows():
            row_errs = []
            
            # Validate coordinates
            try:
                lat = float(row[lat_col])
                lon = float(row[lon_col])
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    row_errs.append(f"Coordinates out of bounds: lat={lat}, lon={lon}")
            except Exception:
                row_errs.append("Invalid or missing coordinate values.")

            # Validate numeric value
            try:
                float(row[val_col])
            except Exception:
                row_errs.append("Observation value is not numeric.")

            if row_errs:
                invalid_count += 1
                errors.append({"row": idx + 1, "message": "; ".join(row_errs)})
            else:
                valid_count += 1

        return {
            "valid_rows": valid_count,
            "invalid_rows": invalid_count,
            "errors": errors
        }

    def ingest(
        self,
        df: pd.DataFrame,
        mapping: dict,
        dataset_name: str,
        layer_type: str,
        user_id: str,
        region_id: str = None
    ) -> dict:
        # Resolve active region
        if not region_id:
            active_region = self.db.query(Region).filter(Region.is_active == True).first()
            if not active_region:
                raise ValueError("No active region configured for ingestion.")
            region_id = active_region.id

        # Resolve or create the custom_import source record
        source = self.db.query(Source).filter(Source.key == "custom_import").first()
        if not source:
            source = Source(
                id=uuid.uuid4(),
                key="custom_import",
                name="Custom User Import",
                category="custom",
                layer_types=["aq", "lst", "ndvi", "fire", "weather"]
            )
            self.db.add(source)
            self.db.commit()

        # Required columns mapping
        lat_col = mapping["latitude"]
        lon_col = mapping["longitude"]
        val_col = mapping["value"]
        
        # Optional columns mapping
        time_col = mapping.get("observed_at")
        station_id_col = mapping.get("station_id")
        station_name_col = mapping.get("station_name")
        unit_col = mapping.get("unit")

        observations = []
        for idx, row in df.iterrows():
            try:
                lat = float(row[lat_col])
                lon = float(row[lon_col])
                val = float(row[val_col])
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    continue
            except Exception:
                continue

            # Parse observed time or default to now
            observed_at = datetime.now(timezone.utc)
            if time_col and pd.notna(row[time_col]):
                try:
                    observed_at = pd.to_datetime(row[time_col]).to_pydatetime()
                    if observed_at.tzinfo is None:
                        observed_at = observed_at.replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            station_id = str(row[station_id_col]) if station_id_col and pd.notna(row[station_id_col]) else None
            station_name = str(row[station_name_col]) if station_name_col and pd.notna(row[station_name_col]) else None
            unit = str(row[unit_col]) if unit_col and pd.notna(row[unit_col]) else None

            # Serialize row payload safely
            raw_payload = row.to_dict()
            cleaned_payload = {}
            for k, v in raw_payload.items():
                if pd.isna(v):
                    cleaned_payload[k] = None
                elif isinstance(v, datetime):
                    cleaned_payload[k] = v.isoformat()
                else:
                    cleaned_payload[k] = v

            # Build observation object
            geom_str = f"SRID=4326;POINT({lon} {lat})"
            observations.append(RawObservation(
                id=uuid.uuid4(),
                source_id=source.id,
                region_id=region_id,
                layer_type=layer_type,
                geometry=geom_str,
                value=val,
                unit=unit,
                station_id=station_id,
                station_name=station_name,
                observed_at=observed_at,
                raw_payload=cleaned_payload
            ))

        if observations:
            self.db.bulk_save_objects(observations)

        # Write ImportDataset metadata record
        dataset_id = uuid.uuid4()
        dataset = ImportDataset(
            id=dataset_id,
            user_id=user_id,
            name=dataset_name,
            format=self.detect_format(dataset_name),
            row_count=len(observations),
            schema_map=mapping,
            layer_type=layer_type,
            mage_pipeline_id=f"custom_import_{dataset_id.hex[:8]}",
            imported_at=datetime.now(timezone.utc),
            is_visible=True
        )
        self.db.add(dataset)
        self.db.commit()

        return {
            "dataset_id": str(dataset_id),
            "ingested": len(observations),
            "total_rows": len(df)
        }
