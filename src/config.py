"""
Centralized configuration for Methane Shadow Hunter.
Loads from .env file and provides typed access to all settings.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env from src directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path(__file__).resolve().parent / ".env")

DATASET_DIR = PROJECT_ROOT / "models" / "dataset"


@dataclass
class Config:
    """All configuration in one place."""

    # --- Data Mode ---
    use_demo_data: bool = True

    # --- CarbonMapper ---
    carbonmapper_token: str = ""
    carbonmapper_stac_url: str = "https://api.carbonmapper.org/api/v1/stac/"

    # --- LLM (Featherless AI - OpenAI-compatible) ---
    featherless_api_key: str = ""
    featherless_model: str = "meta-llama/Llama-3.1-8B-Instruct"
    featherless_base_url: str = "https://api.featherless.ai/v1"

    # --- AOI (India default) ---
    aoi_min_lon: float = 68.0
    aoi_max_lon: float = 97.5
    aoi_min_lat: float = 6.5
    aoi_max_lat: float = 37.0

    # --- Detection ---
    hotspot_threshold_sigma: float = 2.0
    spatial_join_radius_km: float = 5.0

    # --- Paths ---
    dataset_dir: Path = DATASET_DIR

    @classmethod
    def from_env(cls) -> "Config":
        """Build config from environment variables."""
        return cls(
            use_demo_data=os.getenv("USE_DEMO_DATA", "true").lower() == "true",
            carbonmapper_token=os.getenv("CARBONMAPPER_API_TOKEN", ""),
            carbonmapper_stac_url=os.getenv(
                "CARBONMAPPER_STAC_URL",
                "https://api.carbonmapper.org/api/v1/stac/",
            ),
            featherless_api_key=os.getenv("FEATHERLESS_API_KEY", ""),
            featherless_model=os.getenv("FEATHERLESS_MODEL", "meta-llama/Llama-3.1-8B-Instruct"),
            featherless_base_url=os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"),
            aoi_min_lon=float(os.getenv("AOI_MIN_LON", "68.0")),
            aoi_max_lon=float(os.getenv("AOI_MAX_LON", "97.5")),
            aoi_min_lat=float(os.getenv("AOI_MIN_LAT", "6.5")),
            aoi_max_lat=float(os.getenv("AOI_MAX_LAT", "37.0")),
            hotspot_threshold_sigma=float(
                os.getenv("HOTSPOT_THRESHOLD_SIGMA", "2.0")
            ),
            spatial_join_radius_km=float(os.getenv("SPATIAL_JOIN_RADIUS_KM", "5.0")),
            dataset_dir=DATASET_DIR,
        )

    @property
    def aoi_bbox(self) -> tuple:
        """Return (min_lon, min_lat, max_lon, max_lat)."""
        return (self.aoi_min_lon, self.aoi_min_lat, self.aoi_max_lon, self.aoi_max_lat)


# Singleton
config = Config.from_env()
