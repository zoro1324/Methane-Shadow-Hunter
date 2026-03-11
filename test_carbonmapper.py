"""
CarbonMapper API Token Verification Script
==========================================
Run this before pipeline integration to confirm the token is valid
and the STAC API is reachable.

Usage:
    python test_carbonmapper.py
"""

import os
import sys
import json
from pathlib import Path

# Load .env from src/
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / "src" / ".env")

import requests

# ── Config ────────────────────────────────────────────────────────────────────
TOKEN        = os.getenv("CARBONMAPPER_API_TOKEN", "")
STAC_BASE    = os.getenv("CARBONMAPPER_STAC_URL", "https://api.carbonmapper.org/api/v1/stac/")
COLLECTION   = "l4a-ch4-mfa-v3a"

# India bounding box (lon_min, lat_min, lon_max, lat_max)
INDIA_BBOX   = (68.0, 6.5, 97.5, 37.0)
DATE_RANGE   = "2023-01-01/2025-12-31"
LIMIT        = 5   # small limit just for testing

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {TOKEN}",
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def ok(msg):   print(f"  [OK]   {msg}")
def fail(msg): print(f"  [FAIL] {msg}")
def info(msg): print(f"  [INFO] {msg}")

# ── Test 1: Token present ──────────────────────────────────────────────────────
section("1. Token Check")
if not TOKEN:
    fail("CARBONMAPPER_API_TOKEN is not set in src/.env")
    sys.exit(1)
ok(f"Token loaded  ({TOKEN[:20]}...{TOKEN[-10:]})")

# ── Test 2: STAC catalog root ──────────────────────────────────────────────────
section("2. STAC Catalog Root")
try:
    r = requests.get(STAC_BASE, headers=HEADERS, timeout=15)
    r.raise_for_status()
    catalog = r.json()
    ok(f"HTTP {r.status_code} — catalog reachable")
    info(f"Title : {catalog.get('title', 'N/A')}")
    info(f"ID    : {catalog.get('id', 'N/A')}")
except requests.exceptions.HTTPError as e:
    fail(f"HTTP error: {e}")
    sys.exit(1)
except requests.exceptions.ConnectionError as e:
    fail(f"Connection failed — check your internet: {e}")
    sys.exit(1)
except Exception as e:
    fail(f"Unexpected error: {e}")
    sys.exit(1)

# ── Test 3: Collections list ───────────────────────────────────────────────────
section("3. Collections List")
try:
    r = requests.get(f"{STAC_BASE}collections", headers=HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()
    collections = [c.get("id") for c in data.get("collections", [])]
    ok(f"Found {len(collections)} collections")
    for c in collections:
        marker = " <-- target" if c == COLLECTION else ""
        info(f"  {c}{marker}")
    if COLLECTION not in collections:
        fail(f"Target collection '{COLLECTION}' not found!")
except Exception as e:
    fail(f"Could not list collections: {e}")

# ── Test 4: STAC Search (India bbox) ──────────────────────────────────────────
section("4. STAC Search — India BBox (plume count test)")
search_url = f"{STAC_BASE}search"
params = {
    "bbox"       : ",".join(str(b) for b in INDIA_BBOX),
    "datetime"   : DATE_RANGE,
    "limit"      : LIMIT,
    "collections": COLLECTION,
}
try:
    r = requests.get(search_url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    features = data.get("features", [])
    total    = data.get("numberMatched", data.get("context", {}).get("matched", "unknown"))
    ok(f"HTTP {r.status_code} — query successful")
    info(f"Total matched (server) : {total}")
    info(f"Features returned      : {len(features)}")

    if features:
        ok("Sample plumes:")
        for feat in features:
            props = feat.get("properties", {})
            geom  = feat.get("geometry", {})
            coords = geom.get("coordinates", [0, 0])
            if geom.get("type") == "Polygon":
                ring   = coords[0]
                import numpy as np
                lon = round(float(np.mean([c[0] for c in ring])), 4)
                lat = round(float(np.mean([c[1] for c in ring])), 4)
            else:
                lon, lat = round(coords[0], 4), round(coords[1], 4)
            emission = props.get("cm:emission", props.get("emission_rate", "N/A"))
            date     = props.get("datetime", "N/A")
            info(f"  id={feat.get('id')}  lat={lat}  lon={lon}  emission={emission} kg/hr  date={date}")
    else:
        info("No plumes returned for India BBox in the given date range.")
        info("This is expected — the collection covers EMIT instrument overpass areas.")
        info("Try a global bbox (e.g., -180,-90,180,90) to see if any data exists.")

except requests.exceptions.HTTPError as e:
    fail(f"HTTP error on search: {e}")
    if r.status_code == 401:
        fail("401 Unauthorized — token may be expired or invalid.")
    elif r.status_code == 403:
        fail("403 Forbidden — token may not have STAC catalog:read scope.")
except Exception as e:
    fail(f"Search failed: {e}")

# ── Test 5: Global search (sanity check) ──────────────────────────────────────
section("5. Global STAC Search (sanity check, limit=3)")
global_params = {
    "datetime"   : "2024-01-01/2024-12-31",
    "limit"      : 3,
    "collections": COLLECTION,
}
try:
    r = requests.get(search_url, headers=HEADERS, params=global_params, timeout=30)
    r.raise_for_status()
    data     = r.json()
    features = data.get("features", [])
    total    = data.get("numberMatched", "unknown")
    ok(f"Global search — HTTP {r.status_code}")
    info(f"Total in collection (2024): {total}")
    if features:
        ok("Token has valid read access and collection contains data.")
    else:
        info("Collection returned 0 results globally — likely requires different date/bbox.")
except Exception as e:
    fail(f"Global search failed: {e}")

# ── Summary ────────────────────────────────────────────────────────────────────
section("Summary")
print("""
  If all tests show [OK], the token is valid and the API is reachable.
  You can now set USE_DEMO_DATA=False in src/.env to use live data.

  Next step: run the pipeline
      python -c "from src.pipeline import MethaneHunterPipeline; p = MethaneHunterPipeline(); p.run()"
""")
