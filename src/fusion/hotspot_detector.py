"""
Hotspot Detection Module.

Detects methane super-emitter hotspots from Sentinel-5P data
using statistical anomaly detection (mean + N*sigma threshold).
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class DetectedHotspot:
    """A confirmed methane hotspot after threshold filtering."""
    hotspot_id: str
    latitude: float
    longitude: float
    ch4_count: int
    anomaly_score: float
    severity: str
    requires_highres: bool     # Whether to trigger high-res satellite tasking
    priority: int              # 1=highest, 3=lowest


class HotspotDetector:
    """
    Detects methane hotspots from Sentinel-5P observations.
    
    Uses a configurable threshold (mean + N*sigma) to separate
    genuine super-emitter events from natural CH4 variability.
    """

    def __init__(self, threshold_sigma: float = 2.0):
        self.threshold_sigma = threshold_sigma

    def detect(self, hotspots_df: pd.DataFrame) -> list[DetectedHotspot]:
        """
        Filter hotspots using anomaly detection.
        
        Args:
            hotspots_df: DataFrame with columns [latitude, longitude, count, severity]
        
        Returns:
            List of DetectedHotspot objects that exceed the threshold.
        """
        if hotspots_df.empty:
            return []

        mean_count = hotspots_df["count"].mean()
        std_count = hotspots_df["count"].std()
        if pd.isna(std_count) or std_count == 0:
            std_count = 1.0

        threshold = mean_count + self.threshold_sigma * std_count

        detected = []
        for i, row in hotspots_df.iterrows():
            anomaly_score = (row["count"] - mean_count) / std_count

            # Classify priority
            if row["count"] > mean_count + 3 * std_count:
                priority = 1  # Critical - immediate tasking
            elif row["count"] > threshold:
                priority = 2  # High - schedule tasking
            else:
                priority = 3  # Moderate - monitor

            # Only include hotspots above threshold for high-res tasking
            requires_highres = row["count"] > threshold

            detected.append(
                DetectedHotspot(
                    hotspot_id=f"HS-{i:04d}",
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    ch4_count=int(row["count"]),
                    anomaly_score=round(anomaly_score, 3),
                    severity=row.get("severity", "Unknown"),
                    requires_highres=requires_highres,
                    priority=priority,
                )
            )

        # Sort by priority (1 first) then by anomaly score (highest first)
        detected.sort(key=lambda h: (h.priority, -h.anomaly_score))
        return detected

    def get_tasking_candidates(self, detected: list[DetectedHotspot]) -> list[DetectedHotspot]:
        """Return only hotspots that warrant high-res satellite tasking."""
        return [h for h in detected if h.requires_highres]

    def summary(self, detected: list[DetectedHotspot]) -> dict:
        """Return detection summary statistics."""
        tasking = self.get_tasking_candidates(detected)
        return {
            "total_analyzed": len(detected),
            "above_threshold": len(tasking),
            "priority_1_critical": sum(1 for h in detected if h.priority == 1),
            "priority_2_high": sum(1 for h in detected if h.priority == 2),
            "priority_3_moderate": sum(1 for h in detected if h.priority == 3),
            "threshold_sigma": self.threshold_sigma,
            "max_anomaly_score": max((h.anomaly_score for h in detected), default=0),
        }
