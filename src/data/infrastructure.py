"""
Oil & Gas Infrastructure Database.

Loads facility data from GOGI/OGIM or generates synthetic
infrastructure points for India for demo purposes.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class Facility:
    """An oil & gas infrastructure facility."""
    facility_id: str
    name: str
    facility_type: str       # "well", "pipeline", "refinery", "compressor", "terminal"
    latitude: float
    longitude: float
    operator: str
    country: str
    state: str
    status: str              # "active", "inactive", "abandoned"
    capacity: Optional[str] = None


class InfrastructureDB:
    """
    Oil & Gas Infrastructure facility database.
    
    Supports:
    1. Loading from GeoJSON/CSV files (GOGI/OGIM exports)
    2. Synthetic facility generation for India demo
    """

    # Known Indian O&G infrastructure regions (approximate)
    INDIA_OG_REGIONS = [
        # (lat, lon, name, state, type)
        (23.05, 72.58, "Gujarat Petrochemical Complex", "Gujarat", "refinery"),
        (19.97, 72.82, "Mumbai High Offshore", "Maharashtra", "well"),
        (26.85, 70.09, "Barmer-Sanchor Basin", "Rajasthan", "well"),
        (26.92, 70.85, "Jaisalmer Gas Field", "Rajasthan", "well"),
        (22.30, 68.97, "Jamnagar Refinery", "Gujarat", "refinery"),
        (21.77, 72.15, "Hazira Gas Processing", "Gujarat", "compressor"),
        (19.18, 72.96, "BPCL Mumbai Refinery", "Maharashtra", "refinery"),
        (13.10, 80.29, "Chennai Petroleum", "Tamil Nadu", "refinery"),
        (20.27, 85.84, "Paradip Refinery", "Odisha", "refinery"),
        (26.15, 91.73, "Assam Oil Fields", "Assam", "well"),
        (27.18, 95.05, "Digboi Refinery", "Assam", "refinery"),
        (22.32, 73.17, "Vadodara IOCL Refinery", "Gujarat", "refinery"),
        (21.17, 72.83, "Surat Gas Terminal", "Gujarat", "terminal"),
        (23.25, 69.67, "Kutch Basin Fields", "Gujarat", "well"),
        (24.88, 74.63, "Mangala Oil Field", "Rajasthan", "well"),
        (15.40, 73.88, "Goa Pipeline Junction", "Goa", "pipeline"),
        (9.97, 76.24, "Kochi Refinery", "Kerala", "refinery"),
        (17.68, 83.22, "KG Basin Offshore", "Andhra Pradesh", "well"),
        (10.77, 79.83, "Cauvery Basin Field", "Tamil Nadu", "well"),
        (25.62, 85.12, "Barauni Refinery", "Bihar", "refinery"),
        (30.33, 76.36, "Panipat Refinery", "Haryana", "refinery"),
        (28.42, 77.31, "Mathura Refinery", "Uttar Pradesh", "refinery"),
        (22.76, 75.88, "Bina Refinery", "Madhya Pradesh", "refinery"),
        (26.47, 80.35, "ONGC Ankleshwar", "Gujarat", "well"),
        (20.93, 71.37, "Diu Gas Facility", "Gujarat", "compressor"),
    ]

    OPERATORS = [
        "ONGC", "Oil India Limited", "Reliance Industries",
        "BPCL", "HPCL", "IOCL", "GAIL", "Cairn India",
        "Vedanta Resources", "GSPC", "Essar Oil",
    ]

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path
        self._facilities: Optional[list[Facility]] = None

    def load_facilities(self) -> list[Facility]:
        """Load or generate facilities."""
        if self._facilities is not None:
            return self._facilities

        if self.data_path and self.data_path.exists():
            self._facilities = self._load_from_file()
        else:
            self._facilities = self._generate_synthetic()

        return self._facilities

    def _load_from_file(self) -> list[Facility]:
        """Load facilities from CSV or GeoJSON."""
        path = self.data_path
        if path.suffix == ".csv":
            df = pd.read_csv(path)
            return [
                Facility(
                    facility_id=row.get("facility_id", f"FAC-{i:04d}"),
                    name=row.get("name", "Unknown"),
                    facility_type=row.get("type", "well"),
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    operator=row.get("operator", "Unknown"),
                    country=row.get("country", "India"),
                    state=row.get("state", "Unknown"),
                    status=row.get("status", "active"),
                )
                for i, row in df.iterrows()
            ]
        return self._generate_synthetic()

    def _generate_synthetic(self) -> list[Facility]:
        """Generate synthetic O&G facilities across India."""
        rng = np.random.RandomState(123)
        facilities = []

        for i, (lat, lon, name, state, ftype) in enumerate(self.INDIA_OG_REGIONS):
            # Main facility
            facilities.append(
                Facility(
                    facility_id=f"IND-{i:04d}",
                    name=name,
                    facility_type=ftype,
                    latitude=lat,
                    longitude=lon,
                    operator=rng.choice(self.OPERATORS),
                    country="India",
                    state=state,
                    status="active",
                )
            )

            # Add 2-5 nearby sub-facilities (wells, compressors, etc.)
            n_sub = rng.randint(2, 6)
            for j in range(n_sub):
                sub_lat = lat + rng.normal(0, 0.02)
                sub_lon = lon + rng.normal(0, 0.02)
                sub_type = rng.choice(["well", "compressor", "pipeline", "tank_battery"])
                facilities.append(
                    Facility(
                        facility_id=f"IND-{i:04d}-{j:02d}",
                        name=f"{name} - {sub_type.title()} {j+1}",
                        facility_type=sub_type,
                        latitude=round(sub_lat, 6),
                        longitude=round(sub_lon, 6),
                        operator=facilities[-1].operator,
                        country="India",
                        state=state,
                        status=rng.choice(["active", "active", "active", "inactive"]),
                    )
                )

        return facilities

    def facilities_to_dataframe(self, facilities: Optional[list] = None) -> pd.DataFrame:
        """Convert facilities to DataFrame."""
        if facilities is None:
            facilities = self.load_facilities()
        return pd.DataFrame([
            {
                "facility_id": f.facility_id,
                "name": f.name,
                "type": f.facility_type,
                "latitude": f.latitude,
                "longitude": f.longitude,
                "operator": f.operator,
                "country": f.country,
                "state": f.state,
                "status": f.status,
            }
            for f in facilities
        ])

    def find_nearest(self, lat: float, lon: float, radius_km: float = 5.0) -> list[Facility]:
        """Find facilities within radius_km of a point using haversine."""
        facilities = self.load_facilities()
        results = []
        for f in facilities:
            dist = self._haversine(lat, lon, f.latitude, f.longitude)
            if dist <= radius_km:
                results.append((f, dist))
        results.sort(key=lambda x: x[1])
        return [(f, round(d, 2)) for f, d in results]

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2) -> float:
        """Haversine distance in km."""
        R = 6371.0
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = (
            np.sin(dlat / 2) ** 2
            + np.cos(np.radians(lat1))
            * np.cos(np.radians(lat2))
            * np.sin(dlon / 2) ** 2
        )
        return R * 2 * np.arcsin(np.sqrt(a))
