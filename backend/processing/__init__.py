"""
Raphael — Raster Processing Pipeline

Provides satellite imagery processing with automatic mock fallbacks
for environments lacking GDAL/Rasterio/HDF4 drivers.
"""

from processing.raster import (
    generate_mock_lst_tile,
    generate_mock_ndvi_tile,
    generate_thumbnail,
    TILES_DIR,
    HAS_RASTERIO,
    HAS_GDAL,
    HAS_HDF4,
)

__all__ = [
    "generate_mock_lst_tile",
    "generate_mock_ndvi_tile",
    "generate_thumbnail",
    "TILES_DIR",
    "HAS_RASTERIO",
    "HAS_GDAL",
    "HAS_HDF4",
]
