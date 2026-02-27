"""
Wind Field Module.

Provides wind speed and direction for plume modeling.
Demo mode uses configurable constant wind fields.
"""

import numpy as np
import requests
from dataclasses import dataclass
from typing import Optional


@dataclass
class WindData:
    """Wind conditions at a specific location and time."""
    speed_ms: float            # Wind speed (m/s)
    direction_deg: float       # Direction wind is coming FROM (degrees from N)
    u_component: float         # Eastward wind component (m/s)
    v_component: float         # Northward wind component (m/s)
    stability_class: str       # Pasquill-Gifford stability class (A-F)
    source: str                # "synthetic", "era5", etc.


class WindField:
    """
    Wind field provider.
    
    Currently supports synthetic/constant wind fields.
    Can be extended to integrate with ERA5 reanalysis data.
    """

    def __init__(self, default_speed: float = 3.0, default_direction: float = 270.0, use_live: bool = False):
        """
        Args:
            default_speed: default wind speed (m/s)
            default_direction: default direction wind comes FROM (degrees)
            use_live: if True, fetch real-time wind from Open-Meteo API
        """
        self.default_speed = default_speed
        self.default_direction = default_direction
        self.use_live = use_live

    def get_wind(
        self,
        latitude: float,
        longitude: float,
        datetime_str: Optional[str] = None,
    ) -> WindData:
        """
        Get wind conditions at a location.
        
        If use_live is True, fetches current wind speed from Open-Meteo API.
        Otherwise (or on fallback), returns default wind with slight spatial variation.
        """
        speed = None
        direction = None
        source = "synthetic"
        
        if self.use_live:
            try:
                # Open-Meteo free API for current wind (10m above ground)
                # Does not require API key
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": ["wind_speed_10m", "wind_direction_10m"],
                    "wind_speed_unit": "ms"
                }
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    current = data.get("current", {})
                    if "wind_speed_10m" in current and "wind_direction_10m" in current:
                        speed = current["wind_speed_10m"]
                        direction = current["wind_direction_10m"]
                        source = "open-meteo"
            except Exception as e:
                print(f"[WindField] Open-Meteo API fetch failed: {e}. Falling back to synthetic.")

        if speed is None or direction is None:
            # Add some spatial variation
            rng = np.random.RandomState(
                int(abs(latitude * 1000 + longitude * 100)) % 2**31
            )
    
            speed = self.default_speed + rng.uniform(-1.0, 1.0)
            speed = max(speed, 0.5)
    
            direction = self.default_direction + rng.uniform(-30, 30)
            direction = direction % 360

        # Wind components
        dir_rad = np.radians(direction)
        u = -speed * np.sin(dir_rad)  # Eastward
        v = -speed * np.cos(dir_rad)  # Northward

        # Estimate stability class from wind speed (simplified)
        if speed < 2:
            stability = "B"  # Light winds = more unstable
        elif speed < 4:
            stability = "C"
        elif speed < 6:
            stability = "D"  # Neutral
        else:
            stability = "E"  # Strong winds = more stable

        return WindData(
            speed_ms=round(speed, 2),
            direction_deg=round(direction, 1),
            u_component=round(u, 3),
            v_component=round(v, 3),
            stability_class=stability,
            source=source,
        )

    def get_wind_field_grid(
        self,
        lat_range: tuple,
        lon_range: tuple,
        grid_size: int = 10,
    ) -> list[WindData]:
        """Generate a grid of wind data for visualization."""
        lats = np.linspace(lat_range[0], lat_range[1], grid_size)
        lons = np.linspace(lon_range[0], lon_range[1], grid_size)

        winds = []
        for lat in lats:
            for lon in lons:
                winds.append(self.get_wind(lat, lon))
        return winds
