"""
CarbonMapper Plume Data Client.

Queries the CarbonMapper STAC API for methane plume detections.
Falls back to synthetic demo data when API is unavailable.
"""

import json
import requests
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class PlumeObservation:
    """A single methane plume detection from CarbonMapper or synthetic data."""
    plume_id: str
    latitude: float
    longitude: float
    emission_rate_kg_hr: float   # Estimated emission rate
    emission_uncertainty: float  # Uncertainty in kg/hr
    plume_length_m: float        # Length of the plume in meters
    wind_speed_ms: float         # Wind speed at time of observation
    wind_direction_deg: float    # Wind direction (degrees from N)
    acquisition_date: str        # ISO date string
    quality_flag: str            # "good", "fair", "poor"
    sector: str                  # "oil_gas", "landfill", "coal", etc.
    source: str                  # "carbonmapper" or "synthetic"


class CarbonMapperClient:
    """
    Client for CarbonMapper STAC API plume data.
    
    Supports:
    1. Live STAC API queries (with token authentication)
    2. Synthetic demo plumes matched to Sentinel-5P hotspots
    """

    STAC_BASE = "https://api.carbonmapper.org/api/v1/stac/"

    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        if token is None:
            from src.config import config
            token = config.carbonmapper_token
            base_url = config.carbonmapper_stac_url
        self.token = token
        self.base_url = base_url or self.STAC_BASE

    def _headers(self) -> dict:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    # ------------------------------------------------------------------
    # Live STAC API
    # ------------------------------------------------------------------

    def search_plumes(
        self,
        bbox: tuple,
        date_start: str = "2023-01-01",
        date_end: str = "2025-12-31",
        limit: int = 50,
    ) -> list[PlumeObservation]:
        """
        Search CarbonMapper STAC for plumes within a bounding box.
        Returns list of PlumeObservation.
        """
        search_url = f"{self.base_url}search"
        params = {
            "bbox": ",".join(str(b) for b in bbox),
            "datetime": f"{date_start}/{date_end}",
            "limit": limit,
            "collections": "emit-ch4plume-v1",
        }

        try:
            resp = requests.get(
                search_url, headers=self._headers(), params=params, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_stac_features(data.get("features", []))
        except Exception as e:
            print(f"[CarbonMapper] API query failed: {e}")
            print("[CarbonMapper] Falling back to synthetic plume data.")
            return []

    def _parse_stac_features(self, features: list) -> list[PlumeObservation]:
        """Parse STAC GeoJSON features into PlumeObservation objects."""
        plumes = []
        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [0, 0])

            # Handle different geometry types
            if geom.get("type") == "Point":
                lon, lat = coords[0], coords[1]
            elif geom.get("type") == "Polygon":
                # Use centroid of first ring
                ring = coords[0]
                lon = np.mean([c[0] for c in ring])
                lat = np.mean([c[1] for c in ring])
            else:
                lon, lat = coords[0] if coords else 0, coords[1] if len(coords) > 1 else 0

            plumes.append(
                PlumeObservation(
                    plume_id=feat.get("id", "unknown"),
                    latitude=lat,
                    longitude=lon,
                    emission_rate_kg_hr=props.get("Emission", props.get("emission_rate", 0.0)),
                    emission_uncertainty=props.get("Emission Uncertainty", 0.0),
                    plume_length_m=props.get("Plume Length (m)", props.get("plume_length", 0.0)),
                    wind_speed_ms=props.get("Wind Speed (m/s)", props.get("wind_speed", 3.0)),
                    wind_direction_deg=props.get("Wind Direction", props.get("wind_dir", 0.0)),
                    acquisition_date=props.get("datetime", props.get("acquisition_date", "")),
                    quality_flag=props.get("quality_flag", "good"),
                    sector=props.get("sector", "oil_gas"),
                    source="carbonmapper",
                )
            )
        return plumes

    # ------------------------------------------------------------------
    # Synthetic / Demo plume generation
    # ------------------------------------------------------------------

    def generate_synthetic_plumes(
        self, hotspot_coords: list[tuple], n_plumes: int = None
    ) -> list[PlumeObservation]:
        """
        Generate realistic synthetic plumes near given hotspot locations.
        hotspot_coords: list of (lat, lon) tuples from Sentinel-5P hotspots.
        """
        rng = np.random.RandomState(42)
        if n_plumes is None:
            n_plumes = len(hotspot_coords)

        # Sample from hotspot locations with some spatial jitter
        indices = rng.choice(len(hotspot_coords), size=n_plumes, replace=True)

        plumes = []
        for i, idx in enumerate(indices):
            lat, lon = hotspot_coords[idx]
            # Add small jitter (±0.01° ≈ ±1km)
            lat += rng.normal(0, 0.005)
            lon += rng.normal(0, 0.005)

            # Realistic emission rate distribution (log-normal, median ~50 kg/hr)
            emission = float(rng.lognormal(mean=3.9, sigma=1.0))
            uncertainty = emission * rng.uniform(0.1, 0.4)

            plumes.append(
                PlumeObservation(
                    plume_id=f"SYN-{i:04d}",
                    latitude=round(lat, 6),
                    longitude=round(lon, 6),
                    emission_rate_kg_hr=round(emission, 2),
                    emission_uncertainty=round(uncertainty, 2),
                    plume_length_m=round(rng.uniform(50, 2000), 1),
                    wind_speed_ms=round(rng.uniform(1.5, 8.0), 2),
                    wind_direction_deg=round(rng.uniform(0, 360), 1),
                    acquisition_date="2024-06-15",
                    quality_flag=rng.choice(["good", "good", "good", "fair"]),
                    sector=rng.choice(
                        ["oil_gas", "oil_gas", "oil_gas", "landfill", "coal_mine"],
                        p=[0.5, 0.2, 0.1, 0.15, 0.05],
                    ),
                    source="synthetic",
                )
            )
        return plumes

    def plumes_to_dataframe(self, plumes: list[PlumeObservation]) -> pd.DataFrame:
        """Convert plume observations to a DataFrame."""
        records = []
        for p in plumes:
            records.append({
                "plume_id": p.plume_id,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "emission_rate_kg_hr": p.emission_rate_kg_hr,
                "emission_uncertainty": p.emission_uncertainty,
                "plume_length_m": p.plume_length_m,
                "wind_speed_ms": p.wind_speed_ms,
                "wind_direction_deg": p.wind_direction_deg,
                "acquisition_date": p.acquisition_date,
                "quality_flag": p.quality_flag,
                "sector": p.sector,
                "source": p.source,
            })
        return pd.DataFrame(records)
