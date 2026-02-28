"""
Google Earth Engine Service for Methane Shadow Hunter.

Provides Sentinel-5P TROPOMI CH4 data as:
  1. Map tile URLs (for Leaflet TileLayer overlay)
  2. Sampled point arrays (for leaflet.heat heatmap)
"""

import os
import ee
import logging
import numpy as np
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Default timeout (seconds) for any blocking GEE .getInfo() call
# Must be LESS than the frontend axios timeout (12 s) so Django returns
# a proper 503 before the client disconnects (which causes Broken pipe).
GEE_CALL_TIMEOUT = int(os.getenv('GEE_CALL_TIMEOUT', '10'))


def _run_with_timeout(fn, timeout=GEE_CALL_TIMEOUT):
    """
    Run ``fn()`` in a thread.  Raises ``TimeoutError`` if it doesn't finish
    within ``timeout`` seconds, or re-raises any exception from ``fn``.

    IMPORTANT: we must NOT use `with ThreadPoolExecutor() as executor` here.
    The context-manager calls executor.shutdown(wait=True) on exit, which blocks
    until the GEE HTTP retries finish — easily 40-60 s.  Instead we shut down
    with wait=False so the TimeoutError propagates immediately.
    """
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        result = future.result(timeout=timeout)
        executor.shutdown(wait=False)
        return result
    except FuturesTimeoutError:
        # Abandon the thread — let it finish in the background without blocking.
        future.cancel()
        executor.shutdown(wait=False)
        raise TimeoutError(
            f'GEE call timed out after {timeout}s.'
            ' Check Earth Engine authentication and network connectivity.'
        )
    except Exception:
        executor.shutdown(wait=False)
        raise

# Load .env from server directory
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

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
        print('[GEE-SVC] Earth Engine already initialised ✔')
        return
    print(f'[GEE-SVC] Initialising Earth Engine  project={GEE_PROJECT} ...')
    try:
        ee.Initialize(project=GEE_PROJECT)
        _initialized = True
        print('[GEE-SVC] ee.Initialize() succeeded ✔')
    except Exception as init_exc:
        print(f'[GEE-SVC] ee.Initialize() failed: {init_exc}')
        print('[GEE-SVC] Attempting ee.Authenticate() ...')
        try:
            ee.Authenticate()
            ee.Initialize(project=GEE_PROJECT)
            _initialized = True
            print('[GEE-SVC] ee.Authenticate() + ee.Initialize() succeeded ✔')
        except Exception as auth_exc:
            print(f'[GEE-SVC] ✗ Authentication FAILED: {auth_exc}')
            raise


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

    print(f'\n[GEE-SVC] get_heatmap_points called')
    print(f'[GEE-SVC]   days={days}  num_points={num_points}  scale={scale}')
    print(f'[GEE-SVC]   bbox={bbox}')
    print(f'[GEE-SVC]   GEE_CALL_TIMEOUT={GEE_CALL_TIMEOUT}s')

    image, region = _get_ch4_image(days, bbox)
    print('[GEE-SVC]   CH4 image built, starting sample() call with timeout ...')

    # Sample points from the image — wrapped in a timeout so the server
    # never hangs indefinitely when GEE is slow or unreachable.
    logger.debug(
        '[GEE] Sampling CH4 heatmap: days=%s, num_points=%s, scale=%s',
        days, num_points, scale,
    )
    try:
        samples = _run_with_timeout(
            lambda: image.sample(
                region=region,
                scale=scale,
                numPixels=num_points,
                geometries=True,
            ).getInfo()
        )
    except TimeoutError as exc:
        logger.warning('[GEE] Heatmap sample timed out: %s', exc)
        print(f'[GEE-SVC] ✗ sample() TIMED OUT: {exc}')
        raise
    except Exception as exc:
        logger.warning('[GEE] Heatmap sample failed: %s', exc)
        print(f'[GEE-SVC] ✗ sample() EXCEPTION  {type(exc).__name__}: {exc}')
        raise
    logger.debug('[GEE] Sample succeeded, got %d features', len(samples.get('features', [])))
    print(f'[GEE-SVC] ✔ sample() returned {len(samples.get("features", []))} features')

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

    print(f'[GEE-SVC] CH4 stats  min={v_min:.2f}  max={v_max:.2f}  mean={v_mean:.2f}  std={v_std:.2f}  count={len(values)}')
    print(f'[GEE-SVC] Normalised points: {len(points)}')
    if points:
        print(f'[GEE-SVC] Sample (first 3 norm pts): {points[:3]}')
    print(f'[GEE-SVC] get_heatmap_points \u2714 returning\n')

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


def get_hotspots_by_dates(
    start_date: str,
    end_date: str,
    bbox: tuple = DEFAULT_BBOX,
    num_points: int = None,
    scale: int = None,
) -> dict:
    """
    Detect CH4 anomaly hotspots for an explicit date range using Sentinel-5P TROPOMI.

    Algorithm:
      1. Build a mean CH4 image for [start_date, end_date].
      2. Sample `num_points` evenly across the AOI.
      3. Compute z-score = (value - mean) / std for each sample.
      4. Keep only points with z >= 0.5 (above-average CH4).
      5. Classify into Severe / Moderate / Low by z-score thresholds.
      6. Return hotspot list + global stats + tile URL for map overlay.

    Args:
        start_date:  ISO date string 'YYYY-MM-DD'.
        end_date:    ISO date string 'YYYY-MM-DD'.
        bbox:        (min_lon, min_lat, max_lon, max_lat).
        num_points:  Max sample points (default DEFAULT_HEATMAP_NUM_POINTS).
        scale:       Sampling resolution in metres (default DEFAULT_HEATMAP_SCALE).

    Returns:
        {
            "hotspots": [ { id, latitude, longitude, ch4_ppb, anomaly_score, severity, priority, detected_at }, ... ],
            "stats": { mean, std, min, max, count, total_sampled },
            "tile_url": "https://earthengine.googleapis.com/...",  # or None
            "start_date": "YYYY-MM-DD",
            "end_date":   "YYYY-MM-DD",
        }
    """
    if num_points is None:
        num_points = DEFAULT_HEATMAP_NUM_POINTS
    if scale is None:
        scale = DEFAULT_HEATMAP_SCALE

    _ensure_init()

    region = ee.Geometry.BBox(*bbox)

    image = (
        ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_CH4")
        .filterDate(start_date, end_date)
        .filterBounds(region)
        .select("CH4_column_volume_mixing_ratio_dry_air")
        .mean()
        .clip(region)
    )

    # Sample points uniformly across the region — with timeout
    logger.debug(
        '[GEE] Sampling hotspots by dates: %s → %s, num_points=%s, scale=%s',
        start_date, end_date, num_points, scale,
    )
    try:
        samples = _run_with_timeout(
            lambda: image.sample(
                region=region,
                scale=scale,
                numPixels=num_points,
                geometries=True,
            ).getInfo()
        )
    except TimeoutError as exc:
        logger.warning('[GEE] Hotspots-by-dates timed out: %s', exc)
        raise
    except Exception as exc:
        logger.warning('[GEE] Hotspots-by-dates failed: %s', exc)
        raise

    features = samples.get("features", [])
    if not features:
        return {
            "hotspots": [],
            "stats": {},
            "tile_url": None,
            "start_date": start_date,
            "end_date": end_date,
        }

    raw_points = []
    values = []
    for f in features:
        coords = f["geometry"]["coordinates"]
        val = f["properties"].get("CH4_column_volume_mixing_ratio_dry_air")
        if val is not None:
            raw_points.append([coords[1], coords[0], float(val)])  # [lat, lng, ppb]
            values.append(float(val))

    if not values:
        return {
            "hotspots": [],
            "stats": {},
            "tile_url": None,
            "start_date": start_date,
            "end_date": end_date,
        }

    values_arr = np.array(values)
    v_mean = float(np.nanmean(values_arr))
    v_std  = float(np.nanstd(values_arr)) or 1.0
    v_min  = float(np.nanmin(values_arr))
    v_max  = float(np.nanmax(values_arr))

    total_sampled = len(values)

    hotspots = []
    for i, (lat, lng, ch4) in enumerate(raw_points):
        z = (ch4 - v_mean) / v_std
        if z < 0.5:
            continue  # skip near-average and below-average points

        # Severity classification by z-score
        if z >= 3.0:
            severity, priority = "Severe",   1
        elif z >= 2.0:
            severity, priority = "Moderate", 2
        else:
            severity, priority = "Low",      3

        hotspots.append({
            "id":            f"GEE-{i + 1:04d}",
            "latitude":      round(lat, 5),
            "longitude":     round(lng, 5),
            "ch4_ppb":       round(ch4, 2),
            "anomaly_score": round(z, 4),
            "severity":      severity,
            "priority":      priority,
            "detected_at":   end_date,
        })

    # Sort by anomaly score descending (most anomalous first)
    hotspots.sort(key=lambda x: x["anomaly_score"], reverse=True)

    # Get tile URL for Leaflet overlay
    tile_url = None
    try:
        vis_params = {
            "min":     CH4_VIS_PARAMS["min"],
            "max":     CH4_VIS_PARAMS["max"],
            "palette": CH4_VIS_PARAMS["palette"],
        }
        map_id_dict = image.getMapId(vis_params)
        tile_url = map_id_dict["tile_fetcher"].url_format
    except Exception:
        pass  # tile URL is optional — page still works without it

    return {
        "hotspots": hotspots,
        "stats": {
            "mean":          round(v_mean, 2),
            "std":           round(v_std, 2),
            "min":           round(v_min, 2),
            "max":           round(v_max, 2),
            "count":         len(hotspots),
            "total_sampled": total_sampled,
        },
        "tile_url":   tile_url,
        "start_date": start_date,
        "end_date":   end_date,
    }


# ─── Company-centric hotspot detection ────────────────────────────────────

def get_hotspots_by_location(
    center_lat: float,
    center_lng: float,
    radius_km: float,
    start_date: str,
    end_date: str,
    num_points: int = None,
    scale: int = None,
) -> dict:
    """
    Detect CH4 anomaly hotspots around a specific location (company /
    facility) for a given date range using Sentinel-5P TROPOMI.

    Uses ``ee.Geometry.Point().buffer()`` so the query area is a circle
    centred on the supplied coordinates rather than a bounding box.

    Args:
        center_lat:  Latitude of the centre point (facility location).
        center_lng:  Longitude of the centre point.
        radius_km:   Search radius in kilometres.
        start_date:  ISO date string 'YYYY-MM-DD'.
        end_date:    ISO date string 'YYYY-MM-DD'.
        num_points:  Max sample points (default DEFAULT_HEATMAP_NUM_POINTS).
        scale:       Sampling resolution in metres (default DEFAULT_HEATMAP_SCALE).

    Returns:
        {
            "hotspots":   [ { id, latitude, longitude, ch4_ppb, anomaly_score,
                              severity, priority, detected_at, distance_km }, … ],
            "stats":      { mean, std, min, max, count, total_sampled },
            "tile_url":   str | None,
            "today_tile": str | None,   # current-day CH4 snapshot tile
            "start_date": str,
            "end_date":   str,
            "center":     { "lat": float, "lng": float, "radius_km": float },
        }
    """
    if num_points is None:
        num_points = DEFAULT_HEATMAP_NUM_POINTS
    if scale is None:
        scale = DEFAULT_HEATMAP_SCALE

    _ensure_init()

    # Build circular region around the facility
    point = ee.Geometry.Point([center_lng, center_lat])
    region = point.buffer(radius_km * 1000)  # buffer in metres

    # ── Historical image for the requested date range ─────────────────────
    image = (
        ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_CH4")
        .filterDate(start_date, end_date)
        .filterBounds(region)
        .select("CH4_column_volume_mixing_ratio_dry_air")
        .mean()
        .clip(region)
    )

    # Sample points uniformly across the circular region — with timeout
    logger.debug(
        '[GEE] Sampling hotspots by location: center=(%.4f, %.4f), radius=%s km',
        center_lat, center_lng, radius_km,
    )
    try:
        samples = _run_with_timeout(
            lambda: image.sample(
                region=region,
                scale=scale,
                numPixels=num_points,
                geometries=True,
            ).getInfo()
        )
    except TimeoutError as exc:
        logger.warning('[GEE] Hotspots-by-location timed out: %s', exc)
        raise
    except Exception as exc:
        logger.warning('[GEE] Hotspots-by-location failed: %s', exc)
        raise

    features = samples.get("features", [])

    # ── Build raw points list ─────────────────────────────────────────────
    raw_points = []
    values = []
    for f in features:
        coords = f["geometry"]["coordinates"]
        val = f["properties"].get("CH4_column_volume_mixing_ratio_dry_air")
        if val is not None:
            raw_points.append([coords[1], coords[0], float(val)])
            values.append(float(val))

    if not values:
        empty = {
            "hotspots": [], "stats": {}, "tile_url": None, "today_tile": None,
            "start_date": start_date, "end_date": end_date,
            "center": {"lat": center_lat, "lng": center_lng, "radius_km": radius_km},
        }
        # Still try to produce a today tile even when no historical data
        try:
            today_img = (
                ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_CH4")
                .filterDate(
                    ee.Date(datetime.now().strftime("%Y-%m-%d")).advance(-7, "day"),
                    ee.Date(datetime.now().strftime("%Y-%m-%d")),
                )
                .filterBounds(region)
                .select("CH4_column_volume_mixing_ratio_dry_air")
                .mean()
                .clip(region)
            )
            vis = {"min": CH4_VIS_PARAMS["min"], "max": CH4_VIS_PARAMS["max"],
                   "palette": CH4_VIS_PARAMS["palette"]}
            empty["today_tile"] = today_img.getMapId(vis)["tile_fetcher"].url_format
        except Exception:
            pass
        return empty

    values_arr = np.array(values)
    v_mean = float(np.nanmean(values_arr))
    v_std  = float(np.nanstd(values_arr)) or 1.0
    v_min  = float(np.nanmin(values_arr))
    v_max  = float(np.nanmax(values_arr))
    total_sampled = len(values)

    # ── Haversine helper (inline) ─────────────────────────────────────────
    import math

    def _hav(lat1, lon1, lat2, lon2):
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # ── Build hotspot list ────────────────────────────────────────────────
    hotspots = []
    for i, (lat, lng, ch4) in enumerate(raw_points):
        z = (ch4 - v_mean) / v_std
        if z < 0.5:
            continue
        if z >= 3.0:
            severity, priority = "Severe", 1
        elif z >= 2.0:
            severity, priority = "Moderate", 2
        else:
            severity, priority = "Low", 3

        hotspots.append({
            "id":            f"GEE-{i + 1:04d}",
            "latitude":      round(lat, 5),
            "longitude":     round(lng, 5),
            "ch4_ppb":       round(ch4, 2),
            "anomaly_score": round(z, 4),
            "severity":      severity,
            "priority":      priority,
            "detected_at":   end_date,
            "distance_km":   round(_hav(center_lat, center_lng, lat, lng), 2),
        })

    hotspots.sort(key=lambda x: x["anomaly_score"], reverse=True)

    # ── Tile URLs ─────────────────────────────────────────────────────────
    vis = {"min": CH4_VIS_PARAMS["min"], "max": CH4_VIS_PARAMS["max"],
           "palette": CH4_VIS_PARAMS["palette"]}
    tile_url = None
    today_tile = None

    try:
        tile_url = image.getMapId(vis)["tile_fetcher"].url_format
    except Exception:
        pass

    # "Today" snapshot (last 7 days)
    try:
        today_img = (
            ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_CH4")
            .filterDate(
                ee.Date(datetime.now().strftime("%Y-%m-%d")).advance(-7, "day"),
                ee.Date(datetime.now().strftime("%Y-%m-%d")),
            )
            .filterBounds(region)
            .select("CH4_column_volume_mixing_ratio_dry_air")
            .mean()
            .clip(region)
        )
        today_tile = today_img.getMapId(vis)["tile_fetcher"].url_format
    except Exception:
        pass

    return {
        "hotspots": hotspots,
        "stats": {
            "mean":          round(v_mean, 2),
            "std":           round(v_std, 2),
            "min":           round(v_min, 2),
            "max":           round(v_max, 2),
            "count":         len(hotspots),
            "total_sampled": total_sampled,
        },
        "tile_url":   tile_url,
        "today_tile": today_tile,
        "start_date": start_date,
        "end_date":   end_date,
        "center":     {"lat": center_lat, "lng": center_lng, "radius_km": radius_km},
    }
