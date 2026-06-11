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
