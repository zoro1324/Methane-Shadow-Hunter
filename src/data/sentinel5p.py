"""
Sentinel-5P TROPOMI CH4 Data Loader.

Reads the India Methane dataset (CSV hotspots + GeoTIFF rasters)
from the bundled dataset. Also supports GEE live queries if configured.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

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
