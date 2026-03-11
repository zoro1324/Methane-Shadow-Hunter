"""
Sentinel-5P TROPOMI CH4 Data Loader.

Reads the India Methane dataset (CSV hotspots + GeoTIFF rasters)
from the bundled dataset. Also supports GEE live queries if configured.
"""

import json
import time
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import ee

try:
    import rasterio
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False


@dataclass
class CH4Grid:
    """A 2D methane concentration grid with spatial metadata."""
    data: np.ndarray          # 2D array of CH4 values
    transform: object         # Affine transform (from rasterio) or None
    crs: str                  # Coordinate reference system string
    bounds: tuple             # (min_lon, min_lat, max_lon, max_lat)
    nodata: float = -9999.0


@dataclass
class Hotspot:
    """A detected methane hotspot from Sentinel-5P."""
    latitude: float
    longitude: float
    ch4_count: int            # Number of elevated CH4 observations
    anomaly_score: float      # How many sigma above baseline
    severity: str             # "Low", "Moderate", "Severe"


class Sentinel5PClient:
    """
    Loads Sentinel-5P / TROPOMI CH4 data.
    
    Supports two modes:
    1. Local dataset: reads CSV + GeoTIFF from models/dataset/
    2. GEE (future): queries COPERNICUS/S5P/OFFL/L3_CH4
    """

    def __init__(self, dataset_dir: Optional[Path] = None):
        if dataset_dir is None:
            from src.config import config
            dataset_dir = config.dataset_dir
        self.dataset_dir = Path(dataset_dir)
        self._gee_initialized = False

    # ------------------------------------------------------------------
    # GEE live dataset loading
    # ------------------------------------------------------------------

    def initialize_gee(self):
        """Initialize Google Earth Engine."""
        if not self._gee_initialized:
            # Silence googleapiclient's noisy retry WARNING logs
            logging.getLogger('googleapiclient.http').setLevel(logging.ERROR)
            try:
                ee.Initialize(project='ardent-fusion-445310-r2')
            except Exception as e:
                print("Earth Engine not authenticated. Initiating authentication...")
                ee.Authenticate()
                ee.Initialize(project='ardent-fusion-445310-r2')
            self._gee_initialized = True

    # ------------------------------------------------------------------
    # GEE retry helper
    # ------------------------------------------------------------------

    @staticmethod
    def _gee_getinfo_with_retry(ee_object, max_retries: int = 1, base_delay: float = 0.0):
        """
        Call .getInfo() on a GEE object.

        Keeps a single fast attempt so callers can fall back to local data
        quickly when GEE is experiencing an outage.  The underlying
        googleapiclient already does its own retries; we clamp those to 1 as
        well so the total wait before a fallback is < 10 s.
        """
        import ee.data as _eed
        # Suppress googleapiclient's built-in retry loop so we don't wait 30-60 s
        _orig_retries = getattr(_eed, 'MAX_RETRIES', 5)
        try:
            _eed.MAX_RETRIES = 1
        except Exception:
            pass

        last_exc = None
        for attempt in range(max_retries):
            try:
                return ee_object.getInfo()
            except Exception as exc:
                last_exc = exc
                msg = str(exc)
                # Only retry on transient server-side errors
                if "internal error" in msg.lower() or "500" in msg or "EEException" in type(exc).__name__:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        if delay > 0:
                            print(f"[GEE] Transient error on attempt {attempt + 1}/{max_retries}. "
                                  f"Retrying in {delay:.0f}s … ({msg[:120]})")
                            time.sleep(delay)
                else:
                    raise  # non-retryable error — propagate immediately
        try:
            _eed.MAX_RETRIES = _orig_retries
        except Exception:
            pass
        raise last_exc  # all retries exhausted

    def fetch_hotspots_gee(self, bbox: tuple, days: int = 30) -> pd.DataFrame:
        """Fetch real-time Sentinel-5P CH4 anomalous pixels from GEE.

        Falls back to the bundled local CSV if GEE returns persistent
        server-side (HTTP 500) errors after all retries.
        """
        self.initialize_gee()
        
        endDate = ee.Date(datetime.now().strftime('%Y-%m-%d'))
        startDate = endDate.advance(-days, 'day')
        
        region = ee.Geometry.BBox(*bbox)
        
        collection = (ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_CH4')
                      .filterDate(startDate, endDate)
                      .filterBounds(region)
                      .select('CH4_column_volume_mixing_ratio_dry_air'))
        
        # Calculate mean CH4 over the period
        mean_img = collection.mean().clip(region)
        
        # Calculate region stats to find anomaly threshold
        try:
            stats = self._gee_getinfo_with_retry(
                mean_img.reduceRegion(
                    reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
                    geometry=region,
                    scale=10000,
                    maxPixels=1e9
                )
            )
        except Exception as exc:
            print(f"[WARNING] GEE reduceRegion failed after all retries: {exc}")
            print("[WARNING] Falling back to bundled local CSV dataset.")
            return self.load_hotspots_csv()
        
        ch4_mean = stats.get('CH4_column_volume_mixing_ratio_dry_air_mean')
        ch4_std = stats.get('CH4_column_volume_mixing_ratio_dry_air_stdDev')
        
        if ch4_mean is None or ch4_std is None:
            print("[WARNING] Could not compute stats from GEE, falling back to empty DataFrame.")
            return pd.DataFrame(columns=['longitude', 'latitude', 'count', 'severity'])
            
        # Use the configured threshold (minus a small margin so HotspotDetector has a distribution to evaluate)
        from src.config import config
        target_sigma = max(0.0, config.hotspot_threshold_sigma - 0.5)
        
        # Find pixels > mean + sigma
        threshold = ch4_mean + target_sigma * ch4_std
        anomalies = mean_img.updateMask(mean_img.gt(threshold))
        
        # Sample points from the anomalies
        try:
            points = self._gee_getinfo_with_retry(
                anomalies.sample(
                    region=region,
                    scale=10000,
                    numPixels=500,  # Max points to sample as hotspots
                    geometries=True
                )
            )
        except Exception as exc:
            print(f"[WARNING] GEE sample failed after all retries: {exc}")
            print("[WARNING] Falling back to bundled local CSV dataset.")
            return self.load_hotspots_csv()
        
        features = points.get('features', [])
        
        data = []
        for f in features:
            coords = f['geometry']['coordinates']
            val = f['properties'].get('CH4_column_volume_mixing_ratio_dry_air', 0)
            
            # Synthesize a 'count' metric since GEE just gives concentration.
            # Convert the standard deviation deviation back into a synthetic count to match offline logic
            sigma_val = (val - ch4_mean) / ch4_std if ch4_std > 0 else 0
            
            # Map sigma (typically 2 to 5) to a count range ~ 50 to 150
            synthesized_count = int(max(10, min(200, sigma_val * 30)))
            
            if synthesized_count > 120: 
                sev = "Severe"
            elif synthesized_count > 60:
                sev = "Moderate"
            else:
                sev = "Low"
                
            data.append({
                'longitude': coords[0],
                'latitude': coords[1],
                'count': synthesized_count,
                'severity': sev,
                'ch4_val': val
            })
            
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame(columns=['longitude', 'latitude', 'count', 'severity'])
        return df
        
    def get_summary_stats_from_df(self, df: pd.DataFrame) -> dict:
        """Return summary statistics directly from a DataFrame."""
        if df.empty:
            return {
                "total_hotspots": 0,
                "severe_count": 0,
                "moderate_count": 0,
                "low_count": 0,
                "max_count": 0,
                "mean_count": 0.0,
                "lon_range": (0.0, 0.0),
                "lat_range": (0.0, 0.0),
            }
            
        return {
            "total_hotspots": len(df),
            "severe_count": int((df["severity"] == "Severe").sum()),
            "moderate_count": int((df["severity"] == "Moderate").sum()),
            "low_count": int((df["severity"] == "Low").sum()),
            "max_count": int(df["count"].max()),
            "mean_count": round(df["count"].mean(), 2),
            "lon_range": (df["longitude"].min(), df["longitude"].max()),
            "lat_range": (df["latitude"].min(), df["latitude"].max()),
        }

    # ------------------------------------------------------------------
    # Local dataset loading
    # ------------------------------------------------------------------

    def load_hotspots_csv(self) -> pd.DataFrame:
        """Load India_Methane_Hotspots.csv, parse geometry, add severity."""
        csv_path = self.dataset_dir / "India_Methane_Hotspots.csv"
        df = pd.read_csv(csv_path)

        # Parse .geo JSON → lon/lat
        lons, lats = [], []
        for g in df[".geo"]:
            try:
                coords = json.loads(g)["coordinates"]
                lons.append(coords[0])
                lats.append(coords[1])
            except Exception:
                lons.append(None)
                lats.append(None)

        df["longitude"] = pd.to_numeric(lons, errors="coerce")
        df["latitude"] = pd.to_numeric(lats, errors="coerce")
        df = df.dropna(subset=["longitude", "latitude"])

        # Severity classification based on count quantiles
        q50 = df["count"].quantile(0.50)
        q85 = df["count"].quantile(0.85)

        def classify(x):
            if x > q85:
                return "Severe"
            elif x > q50:
                return "Moderate"
            else:
                return "Low"

        df["severity"] = df["count"].apply(classify)
        return df

    def load_ch4_raster(self, filename: str = "India_Methane_Map.tif") -> CH4Grid:
        """Load a GeoTIFF CH4 raster into a CH4Grid object."""
        if not HAS_RASTERIO:
            raise ImportError(
                "rasterio is required to read GeoTIFF files. "
                "Install with: pip install rasterio"
            )

        tif_path = self.dataset_dir / filename
        with rasterio.open(tif_path) as src:
            data = src.read(1)  # First band
            transform = src.transform
            crs = str(src.crs)
            bounds = src.bounds
            nodata = src.nodata if src.nodata is not None else -9999.0

        return CH4Grid(
            data=data,
            transform=transform,
            crs=crs,
            bounds=(bounds.left, bounds.bottom, bounds.right, bounds.top),
            nodata=nodata,
        )

    def get_hotspots(self) -> list[Hotspot]:
        """
        Load hotspots from CSV and return as Hotspot objects
        with anomaly scores computed from the count distribution.
        """
        df = self.load_hotspots_csv()

        mean_count = df["count"].mean()
        std_count = df["count"].std()
        if std_count == 0:
            std_count = 1.0

        hotspots = []
        for _, row in df.iterrows():
            anomaly = (row["count"] - mean_count) / std_count
            hotspots.append(
                Hotspot(
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    ch4_count=int(row["count"]),
                    anomaly_score=round(anomaly, 3),
                    severity=row["severity"],
                )
            )
        return hotspots

    def get_summary_stats(self) -> dict:
        """Return summary statistics of the loaded dataset."""
        df = self.load_hotspots_csv()
        return {
            "total_hotspots": len(df),
            "severe_count": int((df["severity"] == "Severe").sum()),
            "moderate_count": int((df["severity"] == "Moderate").sum()),
            "low_count": int((df["severity"] == "Low").sum()),
            "max_count": int(df["count"].max()),
            "mean_count": round(df["count"].mean(), 2),
            "lon_range": (df["longitude"].min(), df["longitude"].max()),
            "lat_range": (df["latitude"].min(), df["latitude"].max()),
        }
