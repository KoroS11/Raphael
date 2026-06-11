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
