import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.sentinel5p import Sentinel5PClient
from src.fusion.hotspot_detector import HotspotDetector
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.sentinel5p import Sentinel5PClient
from src.data.carbonmapper import CarbonMapperClient
from src.fusion.hotspot_detector import HotspotDetector
from src.config import config


def _seed_facilities(anchor_coords, n_facilities, rng, operators, fac_id_start=1):
    """Generate demo facilities with tight jitter around anchor (lat, lon) pairs."""
    f_types = ["refinery", "well", "compressor", "pipeline", "terminal", "gas_plant", "tank_battery"]
    facilities = []
    fac_id = fac_id_start
    per_anchor = max(1, n_facilities // len(anchor_coords))
    for i, (lat, lon, label) in enumerate(anchor_coords):
        count = per_anchor if i < len(anchor_coords) - 1 else (n_facilities - len(facilities))
        for j in range(count):
            jlat = lat + rng.normal(0, 0.015)   # ±0.015° ≈ ±1.5 km  (well within 5 km join radius)
            jlon = lon + rng.normal(0, 0.015)
            operator = rng.choice(operators)
            f_type   = rng.choice(f_types)
            facilities.append({
                "facility_id": f"DEMO-{fac_id:04d}",
                "name": f"{operator} {f_type.title()} {j+1}",
                "type": f_type,
                "latitude":  round(jlat, 6),
                "longitude": round(jlon, 6),
                "operator": operator,
                "country": "India",
                "state": "Unknown",
                "status": "active",
            })
            fac_id += 1
    return facilities


def main():
    parser = argparse.ArgumentParser(description="Generate demo_industries.csv")
    parser.add_argument(
        "--offline", action="store_true", default=False,
        help="Use bundled CSV instead of live GEE/CarbonMapper APIs",
    )
    args = parser.parse_args()

    rng = np.random.RandomState(42)
    operators = [
        "ONGC", "Oil India Limited", "Reliance Industries",
        "BPCL", "HPCL", "IOCL", "GAIL", "Cairn India",
        "Vedanta Resources", "GSPC", "Essar Oil",
        "Adani Gas", "Tata Petrodyne",
    ]

    # ── Step 1: GEE hotspot anchor points ────────────────────────────────────
    client = Sentinel5PClient()
    if args.offline:
        print("Loading Sentinel-5P hotspots from bundled CSV (offline mode)...")
        df = client.load_hotspots_csv()
    else:
        print("Fetching active Sentinel-5P hotspots from GEE...")
        df = client.fetch_hotspots_gee(bbox=config.aoi_bbox, days=30)

    detector  = HotspotDetector(threshold_sigma=config.hotspot_threshold_sigma)
    detected  = detector.detect(df)
    candidates = detector.get_tasking_candidates(detected)
    zones     = candidates[:15] or detected[:15]
    if not zones:
        print("No GEE hotspots found. Quitting.")
        return

    gee_anchors = [(z.latitude, z.longitude, "gee") for z in zones]
    print(f"  {len(gee_anchors)} GEE anchor zones")

    # ── Step 2: CarbonMapper plume anchor points (live or offline) ────────────
    cm_anchors = []
    if not args.offline:
        print("Fetching CarbonMapper plume locations (365-day window)...")
        cm = CarbonMapperClient()
        end_date   = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        plumes = cm.search_plumes(bbox=config.aoi_bbox, date_start=start_date, date_end=end_date, limit=50)
        if plumes:
            # De-duplicate by rounding to 0.1° grid to avoid massively overweighting one scene
            seen = set()
            for p in plumes:
                key = (round(p.latitude, 1), round(p.longitude, 1))
                if key not in seen:
                    seen.add(key)
                    cm_anchors.append((p.latitude, p.longitude, "carbonmapper"))
            print(f"  {len(cm_anchors)} unique CarbonMapper plume anchor locations")
        else:
            print("  No CarbonMapper plumes returned — using GEE anchors only")
    else:
        print("  Offline mode: skipping CarbonMapper anchor fetch")

    # ── Step 3: Distribute 55 facilities across both anchor sets ─────────────
    all_anchors = gee_anchors + cm_anchors
    print(f"Total anchor points: {len(all_anchors)}")

    # Split budget: 60 % near CarbonMapper plumes (they're the attribution target),
    # 40 % near GEE hotspots (for demo/offline compatibility)
    total = 55
    if cm_anchors:
        cm_budget  = min(total, round(total * 0.60))
        gee_budget = total - cm_budget
        print(f"  Seeding {cm_budget} facilities near CarbonMapper plumes, "
              f"{gee_budget} near GEE hotspots")
        facilities  = _seed_facilities(cm_anchors,  cm_budget,  rng, operators, fac_id_start=1)
        facilities += _seed_facilities(gee_anchors, gee_budget, rng, operators,
                                       fac_id_start=len(facilities) + 1)
    else:
        print(f"  Seeding all {total} facilities near GEE hotspots")
        facilities = _seed_facilities(gee_anchors, total, rng, operators, fac_id_start=1)

    # Trim or pad to exactly 55
    facilities = facilities[:total]
    while len(facilities) < total:
        anchor = rng.choice(all_anchors)
        lat = anchor[0] + rng.normal(0, 0.015)
        lon = anchor[1] + rng.normal(0, 0.015)
        operator = rng.choice(operators)
        f_type   = rng.choice(["refinery", "well", "compressor", "pipeline", "terminal"])
        facilities.append({
            "facility_id": f"DEMO-{len(facilities)+1:04d}",
            "name": f"{operator} {f_type.title()}",
            "type": f_type,
            "latitude":  round(lat, 6),
            "longitude": round(lon, 6),
            "operator": operator,
            "country": "India",
            "state": "Unknown",
            "status": "active",
        })

    out_path = config.dataset_dir / "demo_industries.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(facilities).to_csv(out_path, index=False)
    print(f"Saved {len(facilities)} industries to {out_path}")


if __name__ == "__main__":
    main()
