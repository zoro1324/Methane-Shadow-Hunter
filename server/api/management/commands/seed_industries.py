"""
Management command: seed_industries

Fetches real lat/lon coordinates of steel plants across India from the
OpenStreetMap Overpass API and loads them into the MySQL `facilities`
table via the Facility model.

Multiple OSM tag patterns are queried because Indian steel facilities are
tagged inconsistently in OSM:
  • product=steel
  • name contains "steel" + industrial or landuse=industrial tag
  • Major-brand name search: JSW, TISCO, SAIL, Tata Steel, Jindal, etc.

Usage:
    python manage.py seed_industries
    python manage.py seed_industries --clear   # Wipe Facility table first
"""

import time
import requests
from django.core.management.base import BaseCommand, CommandError
from api.models import Facility


# ────────────────────────────────────────────────────────────────────────────
# India bounding box  (south, west, north, east)
# ────────────────────────────────────────────────────────────────────────────
INDIA_BBOX = "6.5,68.0,37.0,97.5"

# Public Overpass API endpoints tried in order
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# ── Overpass QL sub-queries ──────────────────────────────────────────────────
# Each string is a (label, ql_body) pair. They are merged into one union query
# to minimise round-trips.
# Label is only used for logging.

SUB_QUERIES = [
    (
        "product=steel",
        """  node["product"="steel"]({bbox});
  way["product"="steel"]({bbox});
  relation["product"="steel"]({bbox});""",
    ),
    (
        "industrial tag + 'steel' in name",
        """  node["industrial"]["name"~"steel",i]({bbox});
  way["industrial"]["name"~"steel",i]({bbox});""",
    ),
    (
        "landuse=industrial + 'steel' in name",
        """  node["landuse"="industrial"]["name"~"steel",i]({bbox});
  way["landuse"="industrial"]["name"~"steel",i]({bbox});""",
    ),
    (
        "major Indian steel brands by name",
        r"""  node["name"~"JSW|TISCO|SAIL|Steel Authority|Tata Steel|Jindal|Bhushan Steel|Essar Steel|RINL|Rashtriya Ispat",i]({bbox});
  way["name"~"JSW|TISCO|SAIL|Steel Authority|Tata Steel|Jindal|Bhushan Steel|Essar Steel|RINL|Rashtriya Ispat",i]({bbox});
  relation["name"~"JSW|TISCO|SAIL|Steel Authority|Tata Steel|Jindal|Bhushan Steel|Essar Steel|RINL|Rashtriya Ispat",i]({bbox});""",
    ),
]


def build_union_query() -> str:
    body_parts = "\n".join(sq for _, sq in SUB_QUERIES)
    formatted = body_parts.format(bbox=INDIA_BBOX)
    return f"[out:json][timeout:180];\n(\n{formatted}\n);\nout center tags;"


def fetch_overpass(query: str, stdout) -> list[dict]:
    """POST the query, try each endpoint in turn on failure."""
    last_error = None
    for url in OVERPASS_ENDPOINTS:
        stdout.write(f"  → Endpoint: {url}")
        try:
            resp = requests.post(
                url,
                data={"data": query},
                timeout=200,
                headers={"User-Agent": "MethaneHunter/1.0 (educational research)"},
            )
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
            stdout.write(f"     {len(elements)} raw OSM elements returned.")
            return elements
        except requests.RequestException as exc:
            stdout.write(f"     FAILED ({exc}), switching endpoint …")
            last_error = exc
            time.sleep(3)

    raise CommandError(
        f"All Overpass API endpoints failed. Last error: {last_error}"
    )


def extract_coords(element: dict) -> tuple:
    """Return (lat, lon) or (None, None)."""
    if element["type"] == "node":
        return element.get("lat"), element.get("lon")
    center = element.get("center", {})
    return center.get("lat"), center.get("lon")


def best_tag(tags: dict, *keys: str, default: str = "Unknown") -> str:
    for k in keys:
        v = tags.get(k, "").strip()
        if v:
            return v
    return default


def derive_state(tags: dict) -> str:
    return best_tag(tags, "addr:state", "addr:province", "is_in:state")


def derive_operator(tags: dict) -> str:
    return best_tag(tags, "operator", "owner", "brand", "company")


def make_facility_id(osm_type: str, osm_id: int) -> str:
    prefix = {"node": "N", "way": "W", "relation": "R"}.get(osm_type, "X")
    return f"OSM-{prefix}{osm_id}"


def auto_name(tags: dict, lat: float, lon: float) -> str:
    """Generate a readable name when OSM has no 'name' tag."""
    operator = derive_operator(tags)
    state = derive_state(tags)
    if operator != "Unknown":
        return f"{operator} Steel Plant"
    if state != "Unknown":
        return f"Steel Plant ({state})"
    return f"Steel Plant ({round(lat, 3)}, {round(lon, 3)})"


class Command(BaseCommand):
    help = (
        "Fetch all steel plant locations across India from OpenStreetMap "
        "and store them in the Facility table."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete ALL existing Facility records before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted = Facility.objects.count()
            Facility.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Cleared {deleted} existing Facility records.")
            )

        # ── Step 1: Query Overpass ─────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write("[ Step 1/3 ]  Querying OpenStreetMap Overpass API …")
        self.stdout.write(
            f"  Searching inside India bbox ({INDIA_BBOX}) using "
            f"{len(SUB_QUERIES)} tag patterns:"
        )
        for label, _ in SUB_QUERIES:
            self.stdout.write(f"    • {label}")

        query = build_union_query()
        elements = fetch_overpass(query, self.stdout)

        if not elements:
            self.stdout.write(self.style.WARNING(
                "\nNo elements returned. OSM may have no tagged steel facilities "
                "in India at this time. Try again later."
            ))
            return

        # ── Step 2: Parse ──────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(
            f"[ Step 2/3 ]  Parsing {len(elements)} OSM elements …"
        )

        # Deduplicate by OSM id within the response (union may repeat)
        seen_ids: set[str] = set()
        skipped_no_coords = 0
        auto_named_count = 0

        existing_fids: set[str] = set(
            Facility.objects.filter(facility_id__startswith="OSM-")
            .values_list("facility_id", flat=True)
        )

        to_create: list[Facility] = []
        to_update_objs: list[Facility] = []
        existing_map: dict[str, Facility] = {
            f.facility_id: f
            for f in Facility.objects.filter(facility_id__startswith="OSM-")
        }

        for elem in elements:
            fid = make_facility_id(elem["type"], elem["id"])
            if fid in seen_ids:
                continue
            seen_ids.add(fid)

            lat, lon = extract_coords(elem)
            if lat is None or lon is None:
                skipped_no_coords += 1
                continue

            tags = elem.get("tags", {})
            name = (
                tags.get("name")
                or tags.get("name:en")
                or tags.get("official_name")
                or ""
            ).strip()

            if not name:
                name = auto_name(tags, lat, lon)
                auto_named_count += 1

            operator = derive_operator(tags)
            state = derive_state(tags)
            lat_r = round(lat, 6)
            lon_r = round(lon, 6)

            if fid in existing_map:
                fac = existing_map[fid]
                fac.name = name
                fac.latitude = lat_r
                fac.longitude = lon_r
                fac.operator = operator
                fac.state = state
                to_update_objs.append(fac)
            else:
                to_create.append(Facility(
                    facility_id=fid,
                    name=name,
                    type="other",       # Steel plant maps to "other" in model choices
                    latitude=lat_r,
                    longitude=lon_r,
                    operator=operator,
                    country="India",
                    state=state,
                    status="active",
                ))

        # ── Step 3: Write to DB ────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write("[ Step 3/3 ]  Writing to database …")

        created_count = 0
        updated_count = 0

        if to_create:
            Facility.objects.bulk_create(to_create, ignore_conflicts=True)
            created_count = len(to_create)

        if to_update_objs:
            Facility.objects.bulk_update(
                to_update_objs,
                ["name", "latitude", "longitude", "operator", "state"],
            )
            updated_count = len(to_update_objs)

        # ── Summary ────────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 56))
        self.stdout.write(self.style.SUCCESS("  seed_industries — complete"))
        self.stdout.write(self.style.SUCCESS("=" * 56))
        self.stdout.write(f"  OSM elements received     : {len(elements)}")
        self.stdout.write(f"  Unique after dedup        : {len(seen_ids)}")
        self.stdout.write(f"  Skipped (no coordinates)  : {skipped_no_coords}")
        self.stdout.write(f"  Auto-named (no OSM name)  : {auto_named_count}")
        self.stdout.write(self.style.SUCCESS(
            f"  Created in DB             : {created_count}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  Updated in DB             : {updated_count}"
        ))
        self.stdout.write(
            f"  Total Facilities in DB    : {Facility.objects.count()}"
        )
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "  Run again any time to refresh with the latest OSM data."
            )
        )
