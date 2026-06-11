# Stage 05 — Raster Processing Pipeline (Rasterio + GDAL)

## Prerequisites
Stage 04 completed. GADM boundaries imported. At least one AQ flow returning data.

## Objective
Build the complete satellite imagery processing pipeline using Rasterio and GDAL. This stage produces the LST heatmap tile and NDVI green cover tile visible in the Raphael dashboard mockup — specifically the glowing temperature gradient over the city map and the green vegetation overlay. These are the two raster layers in the bottom panel (Land Surface Temperature thumbnail and NDVI Green Cover thumbnail).

---

## Step 1 — Create the Raster Processing Module

Create `backend/processing/raster.py`:

```python
import os
import uuid
import numpy as np
from pathlib import Path
from datetime import date, datetime, timezone
from typing import Optional, Tuple

import rasterio
from rasterio.mask import mask as rio_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.crs import CRS
from rasterio.transform import from_bounds
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from shapely.geometry import box, mapping

TILES_DIR = Path(os.getenv("RAPHAEL_DATA_DIR", "./data")) / "tiles"
TILES_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CRS = CRS.from_epsg(4326)


def reproject_to_wgs84(src_path: Path, dst_path: Path) -> Path:
    with rasterio.open(src_path) as src:
        if src.crs == TARGET_CRS:
            return src_path

        transform, width, height = calculate_default_transform(
            src.crs, TARGET_CRS, src.width, src.height, *src.bounds
        )
        kwargs = src.meta.copy()
        kwargs.update({
            "crs":       TARGET_CRS,
            "transform": transform,
            "width":     width,
            "height":    height
        })
        with rasterio.open(dst_path, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=TARGET_CRS,
                    resampling=Resampling.bilinear
                )
    return dst_path


def clip_to_bbox(src_path: Path, bbox: Tuple[float,float,float,float], dst_path: Path) -> Path:
    west, south, east, north = bbox
    geom = [mapping(box(west, south, east, north))]

    with rasterio.open(src_path) as src:
        out_image, out_transform = rio_mask(src, geom, crop=True)
        out_meta = src.meta.copy()
        out_meta.update({
            "height":    out_image.shape[1],
            "width":     out_image.shape[2],
            "transform": out_transform
        })
        with rasterio.open(dst_path, "w", **out_meta) as dst:
            dst.write(out_image)

    return dst_path


def apply_colormap(
    array: np.ndarray,
    vmin: float,
    vmax: float,
    colormap: str,
    out_path: Path,
    transform,
    crs
) -> Path:
    array_clipped = np.clip(array, vmin, vmax)
    normed        = (array_clipped - vmin) / (vmax - vmin)
    normed        = np.nan_to_num(normed, nan=0.0)

    cmap    = plt.get_cmap(colormap)
    rgba    = cmap(normed)
    rgba_u8 = (rgba * 255).astype(np.uint8)

    with rasterio.open(
        out_path, "w",
        driver="PNG",
        height=rgba_u8.shape[0],
        width=rgba_u8.shape[1],
        count=4,
        dtype="uint8",
        crs=crs,
        transform=transform
    ) as dst:
        for band in range(4):
            dst.write(rgba_u8[:, :, band], band + 1)

    return out_path


def process_modis_lst(hdf_path: Path, bbox: Tuple, target_date: date) -> Optional[Path]:
    """
    Process a MODIS MOD11A1 HDF4 file into a colored PNG tile for the LST layer.
    Color scale: blue (20C) -> yellow (35C) -> red (50C+)
    """
    try:
        import subprocess
        # Convert HDF4 subdataset to GeoTIFF using GDAL
        subdataset = f'HDF4_EOS:EOS_GRID:"{hdf_path}":MODIS_Grid_Daily_1km_LST:LST_Day_1km'
        raw_tif    = hdf_path.parent / f"lst_raw_{target_date}.tif"

        subprocess.run([
            "gdal_translate", "-of", "GTiff", subdataset, str(raw_tif)
        ], check=True, capture_output=True)

        # Reproject to WGS84
        wgs_tif = hdf_path.parent / f"lst_wgs84_{target_date}.tif"
        reproject_to_wgs84(raw_tif, wgs_tif)

        # Clip to region bounding box
        clipped_tif = hdf_path.parent / f"lst_clipped_{target_date}.tif"
        clip_to_bbox(wgs_tif, bbox, clipped_tif)

        # Read and apply scale factor
        with rasterio.open(clipped_tif) as src:
            data      = src.read(1).astype(float)
            transform = src.transform
            crs       = src.crs

        # MODIS LST scale factor: multiply by 0.02, subtract 273.15 for Celsius
        data[data == 0]   = np.nan  # 0 = fill value
        lst_celsius        = (data * 0.02) - 273.15
        lst_celsius[lst_celsius < -100] = np.nan  # remove invalid

        out_path = TILES_DIR / f"lst_{target_date}.png"

        # Inferno colormap: dark purple (cool) -> orange -> yellow (hot)
        # Custom LST colormap matching the mockup (blue->yellow->red)
        lst_colors = [
            (0.0,  "#0000ff"),  # 20C — blue
            (0.33, "#00ffff"),  # 30C — cyan
            (0.5,  "#ffff00"),  # 35C — yellow
            (0.75, "#ff8800"),  # 42C — orange
            (1.0,  "#ff0000"),  # 50C+ — red
        ]
        cmap = mcolors.LinearSegmentedColormap.from_list("lst_raphael", lst_colors)

        # Render to PNG
        array_clipped = np.clip(lst_celsius, 20, 55)
        normed        = (array_clipped - 20) / (55 - 20)
        normed        = np.nan_to_num(normed, nan=0.0)
        rgba          = cmap(normed)
        # Set alpha to 0 for NaN cells
        rgba[np.isnan(lst_celsius), 3] = 0.0
        rgba_u8 = (rgba * 255).astype(np.uint8)

        with rasterio.open(
            out_path, "w", driver="PNG",
            height=rgba_u8.shape[0], width=rgba_u8.shape[1],
            count=4, dtype="uint8", crs=crs, transform=transform
        ) as dst:
            for band in range(4):
                dst.write(rgba_u8[:, :, band], band + 1)

        # Cleanup temp files
        for tmp in [raw_tif, wgs_tif, clipped_tif]:
            tmp.unlink(missing_ok=True)

        print(f"LST tile written: {out_path}")
        return out_path

    except Exception as e:
        print(f"LST processing failed: {e}")
        return None


def process_sentinel2_ndvi(tif_path: Path, bbox: Tuple, target_date: date) -> Optional[Path]:
    """
    Process a Sentinel-2 GeoTIFF (containing B04 and B08 bands) into NDVI PNG.
    NDVI = (B08 - B04) / (B08 + B04)
    Color scale: brown (dead) -> white (bare) -> light green -> dark green (dense)
    """
    try:
        wgs_tif     = tif_path.parent / f"ndvi_wgs84_{target_date}.tif"
        clipped_tif = tif_path.parent / f"ndvi_clipped_{target_date}.tif"

        reproject_to_wgs84(tif_path, wgs_tif)
        clip_to_bbox(wgs_tif, bbox, clipped_tif)

        with rasterio.open(clipped_tif) as src:
            # Band 1 = B04 (Red), Band 2 = B08 (NIR) per Sentinel-2 convention
            b04       = src.read(1).astype(float)
            b08       = src.read(2).astype(float)
            transform = src.transform
            crs       = src.crs

        # Compute NDVI
        denominator = b08 + b04
        denominator[denominator == 0] = np.nan
        ndvi = (b08 - b04) / denominator
        ndvi = np.clip(ndvi, -1, 1)

        # NDVI colormap matching the mockup (neon green gradient)
        ndvi_colors = [
            (0.0,  "#3d1a00"),  # -1.0 — deep brown (water/bare)
            (0.25, "#8b6914"),  # -0.25 — brown
            (0.4,  "#ffffcc"),  # 0.0  — pale (bare soil)
            (0.55, "#78c679"),  # 0.2  — light green (sparse)
            (0.7,  "#31a354"),  # 0.4  — medium green
            (0.85, "#006837"),  # 0.6  — dense green
            (1.0,  "#00ff88"),  # 0.8+ — neon green (very dense, matches mockup glow)
        ]
        cmap = mcolors.LinearSegmentedColormap.from_list("ndvi_raphael", ndvi_colors)

        out_path = TILES_DIR / f"ndvi_{target_date}.png"
        apply_colormap(ndvi, -0.2, 0.8, "YlGn", out_path, transform, crs)

        # Cleanup
        for tmp in [wgs_tif, clipped_tif]:
            tmp.unlink(missing_ok=True)

        print(f"NDVI tile written: {out_path}")
        return out_path

    except Exception as e:
        print(f"NDVI processing failed: {e}")
        return None


def process_modis_ndvi(hdf_path: Path, bbox: Tuple, target_date: date) -> Optional[Path]:
    """
    Process MODIS MOD13A2 HDF4 file for NDVI.
    Fallback when Sentinel-2 is not available.
    """
    try:
        import subprocess
        subdataset = f'HDF4_EOS:EOS_GRID:"{hdf_path}":MOD_Grid_16DAY_1km_VI:1 km 16 days NDVI'
        raw_tif    = hdf_path.parent / f"ndvi_raw_{target_date}.tif"
        subprocess.run(
            ["gdal_translate", "-of", "GTiff", subdataset, str(raw_tif)],
            check=True, capture_output=True
        )
        wgs_tif     = hdf_path.parent / f"ndvi_wgs84_{target_date}.tif"
        clipped_tif = hdf_path.parent / f"ndvi_clipped_{target_date}.tif"
        reproject_to_wgs84(raw_tif, wgs_tif)
        clip_to_bbox(wgs_tif, bbox, clipped_tif)

        with rasterio.open(clipped_tif) as src:
            data      = src.read(1).astype(float)
            transform = src.transform
            crs       = src.crs

        # MODIS NDVI scale factor: 0.0001
        data[data == -3000] = np.nan  # fill value
        ndvi = data * 0.0001

        out_path = TILES_DIR / f"ndvi_modis_{target_date}.png"
        apply_colormap(ndvi, -0.2, 0.8, "YlGn", out_path, transform, crs)

        for tmp in [raw_tif, wgs_tif, clipped_tif]:
            tmp.unlink(missing_ok=True)

        return out_path

    except Exception as e:
        print(f"MODIS NDVI processing failed: {e}")
        return None


def generate_thumbnail(tile_path: Path, width: int = 380, height: int = 160) -> Path:
    """
    Generate a small thumbnail version of a raster tile.
    Used for the bottom panel LST and NDVI preview cards in the dashboard.
    Matching the mockup: LST card shows 20C-50C color bar, NDVI shows 0.0-1.0 bar.
    """
    with rasterio.open(tile_path) as src:
        from rasterio.enums import Resampling as RioResampling
        data = src.read(
            out_shape=(src.count, height, width),
            resampling=RioResampling.bilinear
        )

    thumb_path = tile_path.parent / f"{tile_path.stem}_thumb.png"
    with rasterio.open(
        thumb_path, "w", driver="PNG",
        height=height, width=width,
        count=src.count, dtype="uint8"
    ) as dst:
        dst.write(data)

    return thumb_path
```

---

## Step 2 — Complete the MODIS LST Prefect Flow

Update `backend/ingestion/flows/lst_modis.py` — replace the stub `process_lst_granule` task with the real implementation:

```python
@task(name="download-and-process-lst", retries=1)
def process_lst_granule(granule: dict, bbox: tuple) -> str:
    import httpx, tempfile
    from processing.raster import process_modis_lst
    from pathlib import Path
    from datetime import date

    username = os.getenv("EARTHDATA_USERNAME", "")
    password = os.getenv("EARTHDATA_PASSWORD", "")

    # Find the HDF4 download link in the granule metadata
    links = granule.get("links", [])
    hdf_link = next(
        (l["href"] for l in links if l.get("href", "").endswith(".hdf")), None
    )
    if not hdf_link:
        print("No HDF download link found in granule")
        return ""

    tmp_dir  = Path(tempfile.mkdtemp())
    hdf_path = tmp_dir / "lst_granule.hdf"

    # NASA Earthdata requires session-based auth
    import requests
    session = requests.Session()
    session.auth = (username, password)
    r = session.get(hdf_link, stream=True, timeout=300)
    r.raise_for_status()
    with open(hdf_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    tile_path = process_modis_lst(hdf_path, bbox, date.today())
    hdf_path.unlink(missing_ok=True)
    return str(tile_path) if tile_path else ""
```

---

## Step 3 — Create NDVI Prefect Flow

Create `backend/ingestion/flows/ndvi_modis.py`:

```python
from prefect import flow, task
import os, uuid
from datetime import date, datetime, timezone
from pathlib import Path
from ingestion.base import BaseIngestionFlow

class MODISNDVIFlow(BaseIngestionFlow):
    source_key = "modis_ndvi"
    layer_type  = "ndvi"

@task(name="fetch-modis-ndvi-granules", retries=2)
def fetch_ndvi_granules(bbox: tuple, target_date: date) -> list:
    import httpx
    username = os.getenv("EARTHDATA_USERNAME", "")
    password = os.getenv("EARTHDATA_PASSWORD", "")
    if not username:
        return []
    west, south, east, north = bbox
    r = httpx.get(
        "https://cmr.earthdata.nasa.gov/search/granules.json",
        params={
            "short_name":   "MOD13A2",
            "version":      "061",
            "temporal":     f"{target_date},{target_date}",
            "bounding_box": f"{west},{south},{east},{north}",
            "page_size":    3
        },
        auth=(username, password),
        timeout=30
    )
    return r.json().get("feed", {}).get("entry", [])

@task(name="download-process-ndvi", retries=1)
def process_ndvi(granule: dict, bbox: tuple) -> str:
    import requests, tempfile
    from processing.raster import process_modis_ndvi
    username = os.getenv("EARTHDATA_USERNAME", "")
    password = os.getenv("EARTHDATA_PASSWORD", "")
    links    = granule.get("links", [])
    hdf_link = next(
        (l["href"] for l in links if l.get("href","").endswith(".hdf")), None
    )
    if not hdf_link:
        return ""
    tmp_dir  = Path(tempfile.mkdtemp())
    hdf_path = tmp_dir / "ndvi_granule.hdf"
    session  = requests.Session()
    session.auth = (username, password)
    r = session.get(hdf_link, stream=True, timeout=300)
    r.raise_for_status()
    with open(hdf_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    tile = process_modis_ndvi(hdf_path, bbox, date.today())
    hdf_path.unlink(missing_ok=True)
    return str(tile) if tile else ""

@task(name="write-ndvi-tile-metadata")
def write_ndvi_metadata(tile_path: str, bbox: tuple):
    if not tile_path:
        return
    from db.connection import SessionLocal
    from db.models import RasterTile, Region
    from geoalchemy2.shape import from_shape
    from shapely.geometry import box as shapely_box
    db = SessionLocal()
    region = db.query(Region).filter(Region.is_active==True).first()
    tile = RasterTile(
        id=uuid.uuid4(),
        layer_type="ndvi",
        region_id=region.id,
        tile_path=tile_path,
        processed_at=datetime.now(timezone.utc),
        valid_date=date.today(),
        resolution_m=1000,
        source="modis_ndvi",
        colormap="YlGn"
    )
    db.add(tile)
    db.commit()
    db.close()

@flow(name="modis-ndvi-ingestion")
def ndvi_modis_flow():
    bbox     = (76.8, 28.4, 77.4, 28.9)
    granules = fetch_ndvi_granules(bbox, date.today())
    if not granules:
        print("No MODIS NDVI granules found")
        return
    tile_path = process_ndvi(granules[0], bbox)
    write_ndvi_metadata(tile_path, bbox)
    print(f"NDVI tile ready: {tile_path}")
```

---

## Step 4 — Create Tile API Endpoint

Add to `backend/api/routes/layers.py`:

```python
from fastapi.responses import FileResponse
from db.models import RasterTile
from pathlib import Path
import os

@router.get("/{layer_type}/tile")
async def get_raster_tile(
    layer_type: str,
    region_id:  str = Query(...),
    thumbnail:  bool = Query(False),
