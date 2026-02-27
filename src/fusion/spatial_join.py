"""
Spatial Join Module.

Performs proximity-based attribution of methane plumes to
oil & gas infrastructure facilities.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class AttributedEmission:
    """A methane plume attributed to a specific facility."""
    plume_id: str
    facility_id: str
    facility_name: str
    facility_type: str
    operator: str
    state: str
    plume_lat: float
    plume_lon: float
    facility_lat: float
    facility_lon: float
    distance_km: float         # Distance between plume and facility
    emission_rate_kg_hr: float
    emission_uncertainty: float
    pinpoint_accuracy_m: float  # Distance in meters (evaluation metric)
    confidence: str            # "high", "medium", "low"


class SpatialJoiner:
    """
    Joins methane plumes with nearest infrastructure facilities.
    
    Uses haversine distance to find the closest facility to each
    detected plume within a configurable radius.
    """

    def __init__(self, radius_km: float = 5.0):
        self.radius_km = radius_km

    def join(
        self,
        plumes: list,
        facilities: list,
    ) -> list[AttributedEmission]:
        """
        Perform spatial join between plumes and facilities.
        Each plume is attributed to its nearest facility within radius.
        """
        from src.data.infrastructure import InfrastructureDB

        attributed = []
        for plume in plumes:
            best_facility = None
            best_dist = float("inf")

            for facility in facilities:
                dist = InfrastructureDB._haversine(
                    plume.latitude, plume.longitude,
                    facility.latitude, facility.longitude,
                )
                if dist < best_dist and dist <= self.radius_km:
                    best_dist = dist
                    best_facility = facility

            if best_facility is not None:
                pinpoint_m = best_dist * 1000  # Convert km to m

                # Confidence based on distance
                if pinpoint_m < 500:
                    confidence = "high"
                elif pinpoint_m < 2000:
                    confidence = "medium"
                else:
                    confidence = "low"

                attributed.append(
                    AttributedEmission(
                        plume_id=plume.plume_id,
                        facility_id=best_facility.facility_id,
                        facility_name=best_facility.name,
                        facility_type=best_facility.facility_type,
                        operator=best_facility.operator,
                        state=best_facility.state,
                        plume_lat=plume.latitude,
                        plume_lon=plume.longitude,
                        facility_lat=best_facility.latitude,
                        facility_lon=best_facility.longitude,
                        distance_km=round(best_dist, 3),
                        emission_rate_kg_hr=plume.emission_rate_kg_hr,
                        emission_uncertainty=getattr(plume, 'emission_uncertainty', 0.0),
                        pinpoint_accuracy_m=round(pinpoint_m, 1),
                        confidence=confidence,
                    )
                )

        # Sort by emission rate (highest first)
        attributed.sort(key=lambda a: -a.emission_rate_kg_hr)
        return attributed

    def to_dataframe(self, attributed: list[AttributedEmission]) -> pd.DataFrame:
        """Convert attributed emissions to DataFrame."""
        return pd.DataFrame([
            {
                "plume_id": a.plume_id,
                "facility_id": a.facility_id,
                "facility_name": a.facility_name,
                "facility_type": a.facility_type,
                "operator": a.operator,
                "state": a.state,
                "plume_lat": a.plume_lat,
                "plume_lon": a.plume_lon,
                "facility_lat": a.facility_lat,
                "facility_lon": a.facility_lon,
                "distance_km": a.distance_km,
                "emission_rate_kg_hr": a.emission_rate_kg_hr,
                "emission_uncertainty": a.emission_uncertainty,
                "pinpoint_accuracy_m": a.pinpoint_accuracy_m,
                "confidence": a.confidence,
            }
            for a in attributed
        ])

    def metrics(self, attributed: list[AttributedEmission]) -> dict:
        """Compute evaluation metrics for the spatial join."""
        if not attributed:
            return {"total_attributed": 0}

        distances = [a.pinpoint_accuracy_m for a in attributed]
        return {
            "total_attributed": len(attributed),
            "mean_pinpoint_accuracy_m": round(np.mean(distances), 1),
            "median_pinpoint_accuracy_m": round(np.median(distances), 1),
            "max_pinpoint_accuracy_m": round(max(distances), 1),
            "pct_within_500m": round(
                100 * sum(1 for d in distances if d < 500) / len(distances), 1
            ),
            "pct_within_1km": round(
                100 * sum(1 for d in distances if d < 1000) / len(distances), 1
            ),
            "high_confidence_pct": round(
                100
                * sum(1 for a in attributed if a.confidence == "high")
                / len(attributed),
                1,
            ),
            "total_emission_rate_kg_hr": round(
                sum(a.emission_rate_kg_hr for a in attributed), 2
            ),
        }
