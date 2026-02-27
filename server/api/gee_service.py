"""
Google Earth Engine Service for Methane Shadow Hunter.

Provides Sentinel-5P TROPOMI CH4 data as:
  1. Map tile URLs (for Leaflet TileLayer overlay)
  2. Sampled point arrays (for leaflet.heat heatmap)
"""

import os
import ee
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load .env from project root (two levels up from this file)
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# ─── Config read from .env ────────────────────────────────────────────────

GEE_PROJECT = os.getenv("GEE_PROJECT", "ardent-fusion-445310-r2")

# Default India AOI bounding box from .env
DEFAULT_BBOX = (
    float(os.getenv("AOI_MIN_LON", "68.0")),
    float(os.getenv("AOI_MIN_LAT", "6.5")),
    float(os.getenv("AOI_MAX_LON", "97.5")),
    float(os.getenv("AOI_MAX_LAT", "37.0")),
)

# Default heatmap query parameters
DEFAULT_HEATMAP_DAYS = int(os.getenv("GEE_HEATMAP_DAYS", "30"))
DEFAULT_HEATMAP_NUM_POINTS = int(os.getenv("GEE_HEATMAP_NUM_POINTS", "1000"))
DEFAULT_HEATMAP_SCALE = int(os.getenv("GEE_HEATMAP_SCALE", "20000"))

# CH4 visualisation range (ppb)
CH4_VIS_PARAMS = {
    "min": int(os.getenv("CH4_VIS_MIN", "1800")),
    "max": int(os.getenv("CH4_VIS_MAX", "1950")),
    "palette": [
        "#fff3e0",  # very low  - warm white
        "#ffcc80",  # low       - light peach
        "#ffa040",  # moderate  - orange
        "#f36f21",  # elevated  - deep orange
        "#e53935",  # high      - red
        "#b71c1c",  # very high - dark red
        "#7f0000",  # extreme   - deep crimson
    ],
    "opacity": 0.65,
}

_initialized = False


def _ensure_init():
    """Initialize Earth Engine if not already done."""
    global _initialized
    if _initialized:
        return
    try:
        ee.Initialize(project=GEE_PROJECT)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)
    _initialized = True


def _get_ch4_image(days: int = 30, bbox: tuple = DEFAULT_BBOX):
    """
    Build a mean CH4 image from Sentinel-5P OFFL L3 over the given period.
    Returns (ee.Image, region).
    """
    _ensure_init()

    end_date = ee.Date(datetime.now().strftime("%Y-%m-%d"))
    start_date = end_date.advance(-days, "day")
    region = ee.Geometry.BBox(*bbox)

    image = (
        ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_CH4")
        .filterDate(start_date, end_date)
        .filterBounds(region)
        .select("CH4_column_volume_mixing_ratio_dry_air")
        .mean()
        .clip(region)
    )
    return image, region


def get_tile_url(days: int = None, bbox: tuple = None) -> dict:
    """
    Generate a GEE tile URL template for Sentinel-5P CH4 data.

    Returns:
        {
            "tile_url": "https://earthengine.googleapis.com/v1/.../{z}/{x}/{y}",
            "attribution": "Copernicus Sentinel-5P / Google Earth Engine",
            "vis_params": { ... },
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
        }
    """
    if days is None:
        days = DEFAULT_HEATMAP_DAYS
    if bbox is None:
        bbox = DEFAULT_BBOX

    image, _ = _get_ch4_image(days, bbox)

    vis_params = {
        "min": CH4_VIS_PARAMS["min"],
        "max": CH4_VIS_PARAMS["max"],
        "palette": CH4_VIS_PARAMS["palette"],
    }

    map_id_dict = image.getMapId(vis_params)
    tile_url = map_id_dict["tile_fetcher"].url_format

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    return {
        "tile_url": tile_url,
        "attribution": "Copernicus Sentinel-5P TROPOMI / Google Earth Engine",
        "vis_params": CH4_VIS_PARAMS,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "days": days,
    }


def get_heatmap_points(
    days: int = None,
    bbox: tuple = None,
    num_points: int = None,
    scale: int = None,
) -> dict:
    """
    Sample CH4 concentration values from GEE as [lat, lng, intensity] points.

    Args:
        days: Number of days to average over.
        bbox: (min_lon, min_lat, max_lon, max_lat).
        num_points: Max number of sample points.
        scale: Sampling resolution in metres.

    Returns:
        {
            "points": [[lat, lng, intensity], ...],  # intensity normalised 0-1
            "stats": { "mean", "std", "min", "max", "count" },
            "raw_points": [[lat, lng, ch4_ppb], ...],
        }
    """
    if days is None:
        days = DEFAULT_HEATMAP_DAYS
    if bbox is None:
        bbox = DEFAULT_BBOX
    if num_points is None:
        num_points = DEFAULT_HEATMAP_NUM_POINTS
    if scale is None:
        scale = DEFAULT_HEATMAP_SCALE
    image, region = _get_ch4_image(days, bbox)

    # Sample points from the image
    samples = image.sample(
        region=region,
        scale=scale,
        numPixels=num_points,
        geometries=True,
    ).getInfo()

    features = samples.get("features", [])
    if not features:
        return {"points": [], "stats": {}, "raw_points": []}

    raw_points = []
    values = []
    for f in features:
        coords = f["geometry"]["coordinates"]
        val = f["properties"].get("CH4_column_volume_mixing_ratio_dry_air")
        if val is not None:
            raw_points.append([coords[1], coords[0], val])  # [lat, lng, ppb]
            values.append(val)

    if not values:
        return {"points": [], "stats": {}, "raw_points": []}

    values = np.array(values)
    v_min = float(np.nanmin(values))
    v_max = float(np.nanmax(values))
    v_mean = float(np.nanmean(values))
    v_std = float(np.nanstd(values))

    # Normalise intensity to 0-1 for leaflet.heat
    spread = v_max - v_min if v_max > v_min else 1.0
    points = [[p[0], p[1], (p[2] - v_min) / spread] for p in raw_points]

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    return {
        "points": points,
        "raw_points": raw_points,
        "stats": {
            "mean": round(v_mean, 2),
            "std": round(v_std, 2),
            "min": round(v_min, 2),
            "max": round(v_max, 2),
            "count": len(values),
        },
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }
