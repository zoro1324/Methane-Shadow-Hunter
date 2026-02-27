import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.sentinel5p import Sentinel5PClient
from src.fusion.hotspot_detector import HotspotDetector
from src.config import config

def main():
    parser = argparse.ArgumentParser(description="Generate demo_industries.csv")
    parser.add_argument(
        "--offline", action="store_true", default=False,
        help="Use bundled India_Methane_Hotspots.csv instead of live GEE (default when --offline not set: live GEE)"
    )
    args = parser.parse_args()

    client = Sentinel5PClient()

    if args.offline:
        print("Loading hotspots from bundled CSV (offline mode)...")
        df = client.load_hotspots_csv()
    else:
        print("Fetching active hotspots from GEE...")
        df = client.fetch_hotspots_gee(bbox=config.aoi_bbox, days=30)
    
    detector = HotspotDetector(threshold_sigma=config.hotspot_threshold_sigma)
    detected = detector.detect(df)
    tasking_candidates = detector.get_tasking_candidates(detected)
    
    # Take up to 15 zones (highest priority first since detect sorts them)
    zones = tasking_candidates[:15]
    if not zones:
        print("No high-priority tasking candidates found. Falling back to any detected hotspots.")
        zones = detected[:15] if len(detected) > 0 else []
    
    if not zones:
        print("No hotspots found at all. Quitting.")
        return

    print(f"Generating industries around {len(zones)} zones...")
    
    facilities = []
    rng = np.random.RandomState(42)
    
    operators = [
        "ONGC", "Oil India Limited", "Reliance Industries",
        "BPCL", "HPCL", "IOCL", "GAIL", "Cairn India",
        "Vedanta Resources", "GSPC", "Essar Oil",
        "Adani Gas", "Tata Petrodyne"
    ]
    
    total_facilities = 55
    facilities_per_zone = max(1, total_facilities // len(zones))
    
    fac_id = 1
    for i, zone in enumerate(zones):
        # Generate several companies near this zone
        for j in range(facilities_per_zone):
            lat = zone.latitude + rng.normal(0, 0.015) # ~1.5km jitter to ensure overlap with 5km join radius
            lon = zone.longitude + rng.normal(0, 0.015)
            
            operator = rng.choice(operators)
            f_type = rng.choice(["refinery", "well", "compressor", "pipeline", "terminal", "gas_plant", "tank_battery"])
            
            facilities.append({
                "facility_id": f"DEMO-{fac_id:04d}",
                "name": f"{operator} {f_type.title()} {j+1}",
                "type": f_type,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "operator": operator,
                "country": "India",
                "state": "Unknown",
                "status": "active"
            })
            fac_id += 1
            
    # Add any remaining to hit exactly 55 if rounding was off
    while len(facilities) < total_facilities:
        zone = rng.choice(zones)
        lat = zone.latitude + rng.normal(0, 0.015)
        lon = zone.longitude + rng.normal(0, 0.015)
        
        operator = rng.choice(operators)
        f_type = rng.choice(["refinery", "well", "compressor", "pipeline", "terminal", "gas_plant", "tank_battery"])
        
        facilities.append({
            "facility_id": f"DEMO-{fac_id:04d}",
            "name": f"{operator} {f_type.title()}",
            "type": f_type,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "operator": operator,
            "country": "India",
            "state": "Unknown",
            "status": "active"
        })
        fac_id += 1
        
    out_path = config.dataset_dir / "demo_industries.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(facilities).to_csv(out_path, index=False)
    print(f"Saved {len(facilities)} industries to {out_path}")

if __name__ == "__main__":
    main()
