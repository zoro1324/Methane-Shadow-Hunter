"""
Satellite Tasking Simulator.

Simulates the process of triggering high-resolution satellite imagery
(GHGSat, Planet, CarbonMapper) for confirmed methane hotspots.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class TaskingRequest:
    """A simulated satellite tasking request."""
    request_id: str
    hotspot_id: str
    latitude: float
    longitude: float
    priority: int
    requested_at: str
    satellite: str               # "GHGSat", "Planet-Tanager", "CarbonMapper"
    status: str                  # "submitted", "acquired", "processing", "delivered"
    estimated_revisit_hrs: float


class TaskingSimulator:
    """
    Simulates high-res satellite tasking for methane hotspots.
    
    In real deployment, this would integrate with satellite APIs.
    Here we simulate the tasking workflow and match hotspots
    with CarbonMapper plume observations.
    """

    SATELLITES = [
        {"name": "CarbonMapper-Tanager", "resolution_m": 30, "revisit_hrs": 72},
    ]

    def __init__(self):
        self.rng = np.random.RandomState(99)
        self.requests: list[TaskingRequest] = []

    def create_tasking_requests(
        self, hotspots: list, max_requests: int = 20
    ) -> list[TaskingRequest]:
        """
        Generate tasking requests for hotspots that require high-res imaging.
        Prioritizes by anomaly score and assigns to optimal satellite.
        """
        # Filter to only those requiring high-res
        candidates = [h for h in hotspots if getattr(h, 'requires_highres', True)]
        candidates = candidates[:max_requests]

        requests = []
        for i, hs in enumerate(candidates):
            sat = self.SATELLITES[i % len(self.SATELLITES)]

            req = TaskingRequest(
                request_id=f"TASK-{i:04d}",
                hotspot_id=getattr(hs, 'hotspot_id', f'HS-{i:04d}'),
                latitude=hs.latitude,
                longitude=hs.longitude,
                priority=getattr(hs, 'priority', 2),
                requested_at=datetime.now().isoformat(),
                satellite=sat["name"],
                status="acquired",  # In demo, assume already acquired
                estimated_revisit_hrs=sat["revisit_hrs"],
            )
            requests.append(req)

        self.requests = requests
        return requests

    def match_with_plumes(
        self,
        requests: list[TaskingRequest],
        plumes: list,
        match_radius_km: float = 5.0,
    ) -> list[dict]:
        """
        Match tasking requests with observed plumes from CarbonMapper.
        Returns list of matched pairs with distance.
        """
        from src.data.infrastructure import InfrastructureDB

        matches = []
        for req in requests:
            for plume in plumes:
                dist = InfrastructureDB._haversine(
                    req.latitude, req.longitude,
                    plume.latitude, plume.longitude,
                )
                if dist <= match_radius_km:
                    matches.append({
                        "request_id": req.request_id,
                        "hotspot_id": req.hotspot_id,
                        "plume_id": plume.plume_id,
                        "distance_km": round(dist, 3),
                        "emission_rate_kg_hr": plume.emission_rate_kg_hr,
                        "satellite": req.satellite,
                        "plume_lat": plume.latitude,
                        "plume_lon": plume.longitude,
                    })

        return matches

    def summary(self) -> dict:
        """Return tasking summary."""
        return {
            "total_requests": len(self.requests),
            "by_satellite": {
                sat["name"]: sum(
                    1 for r in self.requests if r.satellite == sat["name"]
                )
                for sat in self.SATELLITES
            },
            "priority_breakdown": {
                f"P{p}": sum(1 for r in self.requests if r.priority == p)
                for p in [1, 2, 3]
            },
        }
