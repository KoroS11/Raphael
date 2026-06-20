"""
Raphael — Raster Processing Module

Provides satellite imagery processing (LST heat maps, NDVI vegetation maps)
with fail-safe mock fallbacks for environments where GDAL/Rasterio/HDF4
drivers are not available (common on Windows).

Design:
  - Every processing function has a matching `generate_mock_*` fallback
    that produces a synthetic but visually correct PNG tile using only
    numpy + matplotlib (no GDAL/Rasterio required).
  - Module-level capability flags (HAS_GDAL, HAS_RASTERIO, HAS_HDF4)
    are checked once at import time.
  - All paths use pathlib.Path; all tile outputs go to TILES_DIR.
  - Rasterio datasets are opened inside context managers to prevent
    Windows file locking.
"""

import os
import uuid
import numpy as np
from pathlib import Path
from datetime import date, datetime, timezone
from typing import Optional, Tuple, Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server-side rendering
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# ── Capability Flags ─────────────────────────────────────────────────────────

HAS_RASTERIO = False
HAS_GDAL = False
HAS_HDF4 = False

try:
    import rasterio
    from rasterio.mask import mask as rio_mask
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    from rasterio.crs import CRS
    from rasterio.transform import from_bounds
    HAS_RASTERIO = True
except ImportError:
    rasterio = None

try:
    from osgeo import gdal
    HAS_GDAL = True
    if gdal.GetDriverByName("HDF4") is not None:
        HAS_HDF4 = True
except ImportError:
    gdal = None

try:
    from shapely.geometry import box, mapping
except ImportError:
    # shapely is required by geoalchemy2 so this should always be available
    box = None
    mapping = None

# ── Tile Directory ───────────────────────────────────────────────────────────

# Resolve TILES_DIR relative to project root, not cwd
_project_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TILES_DIR = Path(os.getenv("RAPHAEL_DATA_DIR", str(_project_root / "data"))) / "tiles"
TILES_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CRS = None
if HAS_RASTERIO:
    TARGET_CRS = CRS.from_epsg(4326)

print(f"[raster] Capabilities: GDAL={HAS_GDAL}, Rasterio={HAS_RASTERIO}, HDF4={HAS_HDF4}")
print(f"[raster] Tiles directory: {TILES_DIR}")


# ══════════════════════════════════════════════════════════════════════════════
# MOCK TILE GENERATORS (numpy + matplotlib only — always available)
# ══════════════════════════════════════════════════════════════════════════════

def _perlin_like_noise(width: int, height: int, scale: float = 5.0, seed: int = None) -> np.ndarray:
    """
    Generate smooth noise resembling spatial data using multiple octaves
    of interpolated random grids. Pure numpy, no external deps.
    """
    if seed is not None:
        rng = np.random.RandomState(seed)
    else:
        rng = np.random.RandomState()

    result = np.zeros((height, width), dtype=float)
    amplitude = 1.0
    frequency = 1.0

    for octave in range(4):
        # Create a small random grid and interpolate to full size
        grid_h = max(2, int(scale * frequency))
        grid_w = max(2, int(scale * frequency))
        small = rng.rand(grid_h, grid_w)

        # Bilinear interpolation to full size
        from scipy.ndimage import zoom
        factor_h = height / grid_h
        factor_w = width / grid_w
        upscaled = zoom(small, (factor_h, factor_w), order=1)

        # Ensure exact dimensions
        upscaled = upscaled[:height, :width]
        result += amplitude * upscaled

        amplitude *= 0.5
        frequency *= 2.0

    # Normalize to [0, 1]
    result = (result - result.min()) / (result.max() - result.min() + 1e-8)
    return result


def generate_mock_lst_tile(
    bounds: Tuple[float, float, float, float],
    output_path: Optional[Path] = None,
    width: int = 512,
    height: int = 512,
    target_date: Optional[date] = None
) -> Path:
    """
    Generate a synthetic Land Surface Temperature tile.
    Produces a visually correct heat map (plasma colormap) with Perlin-like noise
    centered on Delhi's typical LST range (25°C - 50°C).

    Args:
        bounds: (west, south, east, north) in WGS84
        output_path: Where to save the PNG. Auto-generated if None.
        width: Tile width in pixels
        height: Tile height in pixels
        target_date: Date for filename. Defaults to today.

    Returns:
        Path to the generated PNG tile.
    """
    if target_date is None:
        target_date = date.today()

    if output_path is None:
        lst_dir = TILES_DIR / "lst"
        lst_dir.mkdir(parents=True, exist_ok=True)
        output_path = lst_dir / f"lst_mock_{target_date}.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate spatially-coherent noise
    seed = int(target_date.toordinal()) % (2**31)
    noise = _perlin_like_noise(width, height, scale=6.0, seed=seed)

    # Map to realistic LST range for Delhi (25°C center to 50°C edges)
    # Urban heat island: hotter in center, cooler at edges with some variation
    y_grid, x_grid = np.mgrid[0:height, 0:width]
    cx, cy = width / 2, height / 2
    dist = np.sqrt((x_grid - cx)**2 + (y_grid - cy)**2) / max(width, height)

    # Urban heat island pattern: hotter in center
    uhi = 1.0 - dist * 0.6
    combined = 0.6 * uhi + 0.4 * noise

    # Map to temperature range 25-50°C
    lst_celsius = 25.0 + combined * 25.0

    # Custom LST colormap matching the Raphael dashboard mockup
    lst_colors = [
        (0.0,  "#0000ff"),   # 25°C — blue  (cool)
        (0.25, "#00ffff"),   # 31°C — cyan
        (0.45, "#ffff00"),   # 36°C — yellow
        (0.65, "#ff8800"),   # 41°C — orange
        (0.85, "#ff0000"),   # 46°C — red   (hot)
        (1.0,  "#880000"),   # 50°C — dark red (extreme)
    ]
    cmap = mcolors.LinearSegmentedColormap.from_list("lst_raphael", lst_colors)

    # Normalize to 0-1 for colormap
    normed = (lst_celsius - 20.0) / (55.0 - 20.0)
    normed = np.clip(normed, 0.0, 1.0)

    # Render
    fig, ax = plt.subplots(1, 1, figsize=(width/100, height/100), dpi=100)
    ax.imshow(normed, cmap=cmap, vmin=0, vmax=1, aspect='auto',
              extent=[bounds[0], bounds[2], bounds[1], bounds[3]])
    ax.axis('off')
    fig.savefig(str(output_path), bbox_inches='tight', pad_inches=0,
                transparent=True, dpi=100)
    plt.close(fig)

    print(f"[raster] Mock LST tile generated: {output_path} ({output_path.stat().st_size} bytes)")
    return output_path


def generate_mock_ndvi_tile(
    bounds: Tuple[float, float, float, float],
    output_path: Optional[Path] = None,
    width: int = 512,
    height: int = 512,
    target_date: Optional[date] = None
) -> Path:
    """
    Generate a synthetic NDVI (vegetation) tile.
    Produces a visually correct vegetation map (RdYlGn colormap) with realistic
    NDVI patterns (0.0-0.8) — urban areas low, parks/green belts high.

    Args:
        bounds: (west, south, east, north) in WGS84
        output_path: Where to save the PNG. Auto-generated if None.
        width: Tile width in pixels
        height: Tile height in pixels
        target_date: Date for filename. Defaults to today.

    Returns:
        Path to the generated PNG tile.
    """
    if target_date is None:
        target_date = date.today()

    if output_path is None:
        ndvi_dir = TILES_DIR / "ndvi"
        ndvi_dir.mkdir(parents=True, exist_ok=True)
        output_path = ndvi_dir / f"ndvi_mock_{target_date}.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

