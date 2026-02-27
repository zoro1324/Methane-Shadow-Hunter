"""
Management command: seed_data

Loads demo_industries.csv and India_Methane_Hotspots.csv into the MySQL database.

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear   # Wipe tables first
"""

import csv
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Facility, MethaneHotspot


class Command(BaseCommand):
    help = 'Seed the database with demo industries and methane hotspot data from CSV files.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing Facility and MethaneHotspot records before seeding.',
        )

    def handle(self, *args, **options):
        dataset_dir = settings.DATASET_DIR

        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Facility.objects.all().delete()
            MethaneHotspot.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared.'))

        # ── Seed Facilities from demo_industries.csv ────────────────────
        industries_path = dataset_dir / 'demo_industries.csv'
        if industries_path.exists():
            self.stdout.write(f'Loading facilities from {industries_path}...')
            count = self._seed_facilities(industries_path)
            self.stdout.write(self.style.SUCCESS(f'  → {count} facilities loaded.'))
        else:
            self.stdout.write(self.style.ERROR(f'File not found: {industries_path}'))

        # ── Seed Methane Hotspots from India_Methane_Hotspots.csv ───────
        hotspots_path = dataset_dir / 'India_Methane_Hotspots.csv'
        if hotspots_path.exists():
            self.stdout.write(f'Loading methane hotspots from {hotspots_path}...')
            count = self._seed_hotspots(hotspots_path)
            self.stdout.write(self.style.SUCCESS(f'  → {count} hotspots loaded.'))
        else:
            self.stdout.write(self.style.ERROR(f'File not found: {hotspots_path}'))

        # ── Summary ─────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Seed Complete ==='))
        self.stdout.write(f'  Facilities in DB:      {Facility.objects.count()}')
        self.stdout.write(f'  Methane Hotspots in DB: {MethaneHotspot.objects.count()}')

    def _seed_facilities(self, csv_path: Path) -> int:
        """Load demo_industries.csv into Facility table."""
        existing_ids = set(Facility.objects.values_list('facility_id', flat=True))
        objs = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                fid = row['facility_id'].strip()
                if fid in existing_ids:
                    continue
                objs.append(Facility(
                    facility_id=fid,
                    name=row['name'].strip(),
                    type=row['type'].strip(),
                    latitude=float(row['latitude']),
                    longitude=float(row['longitude']),
                    operator=row['operator'].strip(),
                    country=row.get('country', 'India').strip(),
                    state=row.get('state', 'Unknown').strip(),
                    status=row.get('status', 'active').strip(),
                ))

        if objs:
            Facility.objects.bulk_create(objs, ignore_conflicts=True)
        return len(objs)

    def _seed_hotspots(self, csv_path: Path) -> int:
        """Load India_Methane_Hotspots.csv into MethaneHotspot table."""
        existing_idx = set(MethaneHotspot.objects.values_list('system_index', flat=True))
        objs = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sys_index = row['system:index'].strip()
                if sys_index in existing_idx:
                    continue

                count = int(row['count'])
                label = int(row['label'])

                # Parse coordinates from .geo JSON
                geo = json.loads(row['.geo'])
                coords = geo.get('coordinates', [0, 0])
                longitude = coords[0]
                latitude = coords[1]

                # Classify severity by count
                if count >= 50:
                    severity = 'Severe'
                elif count >= 10:
                    severity = 'Moderate'
                else:
                    severity = 'Low'

                objs.append(MethaneHotspot(
                    system_index=sys_index,
                    count=count,
                    label=label,
                    latitude=latitude,
                    longitude=longitude,
                    severity=severity,
                ))

        if objs:
            MethaneHotspot.objects.bulk_create(objs, ignore_conflicts=True)
        return len(objs)
