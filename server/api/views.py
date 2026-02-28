"""
Methane Shadow Hunter - REST API Views.

Provides endpoints for:
- Facilities CRUD & geo-search
- Methane hotspots (raw + detected)
- Plume observations
- Attributed emissions (spatial join results)
- Inversion results
- Satellite tasking requests
- Audit reports
- Pipeline run trigger & status
- Dashboard summary
"""

import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

from django.conf import settings
from django.db.models import Count, Avg, Sum, Max, Min, Q, F
from django.utils import timezone

from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Facility,
    MethaneHotspot,
    DetectedHotspot,
    PlumeObservation,
    AttributedEmission,
    InversionResult,
    TaskingRequest,
    AuditReport,
    PipelineRun,
)
from .serializers import (
    FacilitySerializer,
    FacilityListSerializer,
    MethaneHotspotSerializer,
    DetectedHotspotSerializer,
    PlumeObservationSerializer,
    AttributedEmissionSerializer,
    AttributedEmissionDetailSerializer,
    InversionResultSerializer,
    TaskingRequestSerializer,
    AuditReportSerializer,
    AuditReportListSerializer,
    PipelineRunSerializer,
    PipelineRunDetailSerializer,
    PipelineTriggerSerializer,
    RegisterSerializer,
    LoginSerializer,
)


# ─── Facility ViewSet ──────────────────────────────────────────────────────

class FacilityViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoints for oil & gas facilities.

    GET  /api/facilities/          → list all
    GET  /api/facilities/<pk>/     → detail
    POST /api/facilities/          → create
    GET  /api/facilities/by_type/  → group by type
    GET  /api/facilities/by_operator/ → group by operator
    GET  /api/facilities/nearby/?lat=&lon=&radius_km= → geo search
    """
    queryset = Facility.objects.all()
    serializer_class = FacilitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'operator', 'state', 'status', 'country']
    search_fields = ['name', 'operator', 'facility_id']
    ordering_fields = ['name', 'operator', 'type', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return FacilityListSerializer
        return FacilitySerializer

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Facility count grouped by type."""
        data = (
            Facility.objects.values('type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        return Response(list(data))

    @action(detail=False, methods=['get'])
    def by_operator(self, request):
        """Facility count grouped by operator."""
        data = (
            Facility.objects.values('operator')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        return Response(list(data))

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Find facilities near a given lat/lon within radius_km."""
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        radius_km = float(request.query_params.get('radius_km', 10))

        if not lat or not lon:
            return Response(
                {'error': 'lat and lon query parameters are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lat, lon = float(lat), float(lon)
        facilities = Facility.objects.all()
        results = []
        for f in facilities:
            dist = _haversine(lat, lon, float(f.latitude), float(f.longitude))
            if dist <= radius_km:
                data = FacilityListSerializer(f).data
                data['distance_km'] = round(dist, 3)
                results.append(data)

        results.sort(key=lambda x: x['distance_km'])
        return Response(results)


# ─── Methane Hotspot ViewSet ───────────────────────────────────────────────

class MethaneHotspotViewSet(viewsets.ModelViewSet):
    """Raw Sentinel-5P methane hotspot observations."""
    queryset = MethaneHotspot.objects.all()
    serializer_class = MethaneHotspotSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['severity', 'label']
    ordering_fields = ['count', 'latitude', 'longitude']

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Summary statistics for methane hotspots."""
        qs = MethaneHotspot.objects.all()
        total = qs.count()
        if total == 0:
            return Response({'total': 0})

        severe = qs.filter(severity='Severe').count()
        moderate = qs.filter(severity='Moderate').count()
        low = qs.filter(severity='Low').count()

        from django.db.models import Max, Min
        agg = qs.aggregate(
            max_count=Max('count'),
            min_count=Min('count'),
            avg_count=Avg('count'),
            min_lat=Min('latitude'),
            max_lat=Max('latitude'),
            min_lon=Min('longitude'),
            max_lon=Max('longitude'),
        )

        return Response({
            'total_hotspots': total,
            'severe_count': severe,
            'moderate_count': moderate,
            'low_count': low,
            'max_count': agg['max_count'],
            'min_count': agg['min_count'],
            'avg_count': round(float(agg['avg_count']), 2),
            'lat_range': [float(agg['min_lat']), float(agg['max_lat'])],
            'lon_range': [float(agg['min_lon']), float(agg['max_lon'])],
        })


# ─── Detected Hotspot ViewSet ─────────────────────────────────────────────

class DetectedHotspotViewSet(viewsets.ModelViewSet):
    """Anomaly-filtered detected hotspots."""
    queryset = DetectedHotspot.objects.all()
    serializer_class = DetectedHotspotSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['priority', 'severity', 'requires_highres', 'pipeline_run']
    ordering_fields = ['priority', 'anomaly_score', 'ch4_count']


# ─── Plume Observation ViewSet ─────────────────────────────────────────────

class PlumeObservationViewSet(viewsets.ModelViewSet):
    """CarbonMapper plume observations."""
    queryset = PlumeObservation.objects.all()
    serializer_class = PlumeObservationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['sector', 'is_synthetic', 'pipeline_run']
    ordering_fields = ['emission_rate_kg_hr', 'wind_speed_ms', 'observed_at']


# ─── Attributed Emission ViewSet ──────────────────────────────────────────

class AttributedEmissionViewSet(viewsets.ModelViewSet):
    """Spatial join results: plume → facility attribution."""
    queryset = AttributedEmission.objects.select_related('facility', 'plume').all()
    serializer_class = AttributedEmissionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['confidence', 'facility', 'pipeline_run']
    ordering_fields = ['emission_rate_kg_hr', 'distance_km']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AttributedEmissionDetailSerializer
        return AttributedEmissionSerializer

    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """Pinpoint accuracy and emission metrics."""
        qs = AttributedEmission.objects.all()
        run_id = request.query_params.get('pipeline_run')
        if run_id:
            qs = qs.filter(pipeline_run_id=run_id)

        total = qs.count()
        if total == 0:
            return Response({'total': 0})

        high_conf = qs.filter(confidence='high').count()
        medium_conf = qs.filter(confidence='medium').count()
        low_conf = qs.filter(confidence='low').count()

        agg = qs.aggregate(
            avg_distance=Avg('distance_km'),
            total_emission=Sum('emission_rate_kg_hr'),
            avg_emission=Avg('emission_rate_kg_hr'),
        )

        return Response({
            'total_attributions': total,
            'high_confidence': high_conf,
            'medium_confidence': medium_conf,
            'low_confidence': low_conf,
            'high_confidence_pct': round(high_conf / total * 100, 1),
            'avg_pinpoint_distance_km': round(float(agg['avg_distance']), 3),
            'total_emission_rate_kg_hr': round(float(agg['total_emission']), 2),
            'avg_emission_rate_kg_hr': round(float(agg['avg_emission']), 2),
        })


# ─── Inversion Result ViewSet ─────────────────────────────────────────────

class InversionResultViewSet(viewsets.ModelViewSet):
    """Gaussian plume inversion results."""
    queryset = InversionResult.objects.select_related('attribution').all()
    serializer_class = InversionResultSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['converged', 'pipeline_run']
    ordering_fields = ['estimated_q_kg_hr', 'error_pct']

    @action(detail=False, methods=['get'])
    def accuracy(self, request):
        """Emission rate error metrics (evaluation metric)."""
        qs = InversionResult.objects.exclude(error_pct__isnull=True)
        run_id = request.query_params.get('pipeline_run')
        if run_id:
            qs = qs.filter(pipeline_run_id=run_id)

        total = qs.count()
        if total == 0:
            return Response({'total': 0})

        agg = qs.aggregate(
            avg_error=Avg('error_pct'),
            max_error=Max('error_pct'),
            min_error=Min('error_pct'),
        )
        converged = qs.filter(converged=True).count()

        return Response({
            'total_inversions': total,
            'converged': converged,
            'convergence_rate_pct': round(converged / total * 100, 1),
            'avg_emission_rate_error_pct': round(float(agg['avg_error']), 2),
            'max_error_pct': round(float(agg['max_error']), 2),
            'min_error_pct': round(float(agg['min_error']), 2),
        })


# ─── Tasking Request ViewSet ──────────────────────────────────────────────

class TaskingRequestViewSet(viewsets.ModelViewSet):
    """Satellite tasking requests."""
    queryset = TaskingRequest.objects.all()
    serializer_class = TaskingRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['satellite', 'priority', 'status', 'pipeline_run']
    ordering_fields = ['priority', 'requested_at']


# ─── Audit Report ViewSet ─────────────────────────────────────────────────

class AuditReportViewSet(viewsets.ModelViewSet):
    """Compliance audit reports."""
    queryset = AuditReport.objects.select_related('facility').all()
    serializer_class = AuditReportSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['risk_level', 'confidence', 'facility', 'pipeline_run']
    search_fields = ['report_id', 'facility__name', 'executive_summary']
    ordering_fields = ['emission_rate_kg_hr', 'risk_level', 'generated_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return AuditReportListSerializer
        return AuditReportSerializer


# ─── Pipeline Run ViewSet ─────────────────────────────────────────────────

class PipelineRunViewSet(viewsets.ModelViewSet):
    """Pipeline execution tracking."""
    queryset = PipelineRun.objects.all()
    serializer_class = PipelineRunSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'mode']
    ordering_fields = ['started_at', 'status']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PipelineRunDetailSerializer
        return PipelineRunSerializer

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Full results for a pipeline run."""
        run = self.get_object()
        return Response(PipelineRunDetailSerializer(run).data)


# ─── Pipeline Trigger ──────────────────────────────────────────────────────

class PipelineTriggerView(APIView):
    """
    POST /api/pipeline/trigger/

    Spawns the pipeline in a background thread and returns 202 immediately
    with the run ID. Poll GET /api/pipeline-runs/{id}/ to track progress.
    """

    def post(self, request):
        import threading

        serializer = PipelineTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mode = serializer.validated_data.get('mode', 'demo')
        use_llm = serializer.validated_data.get('use_llm', False)

        # Create pipeline run record immediately
        run = PipelineRun.objects.create(
            mode=mode,
            use_llm=use_llm,
            status='running',
        )

        # Run pipeline in background thread so the HTTP request returns fast
        thread = threading.Thread(
            target=_run_pipeline_background,
            args=(run.pk, mode, use_llm),
            daemon=True,
        )
        thread.start()

        return Response(
            {'run_id': run.pk, 'status': 'running', 'message': 'Pipeline started. Poll /api/pipeline-runs/{run_id}/ for status.'},
            status=status.HTTP_202_ACCEPTED,
        )


# ─── Terminal colour helpers (used by background pipeline logger) ─────────────
class _C:
    RESET   = "\033[0m";  BOLD    = "\033[1m";  DIM     = "\033[2m"
    GREEN   = "\033[92m"; YELLOW  = "\033[93m"; RED     = "\033[91m"
    CYAN    = "\033[96m"; MAGENTA = "\033[95m"; BLUE    = "\033[94m"
    WHITE   = "\033[97m"

def _pc(text, colour):   return f"{colour}{text}{_C.RESET}"
def _ok(t):   return _pc(f"  ✔  {t}", _C.GREEN)
def _inf(t):  return _pc(f"  ·  {t}", _C.CYAN)
def _warn(t): return _pc(f"  ⚠  {t}", _C.YELLOW)
def _dat(t):  return f"     {_C.DIM}{t}{_C.RESET}"

_STEP_META = {
    1: ("🌍", "Fast Global Sweep",        "Sentinel-5P TROPOMI — 30-day CH4 mosaic over India AOI"),
    2: ("🔍", "Anomaly Detection",         "Statistical σ-threshold → isolate genuine super-emitters"),
    3: ("📡", "High-Res Tasking Trigger",  "Simulating CarbonMapper Tanager / GHGSat acquisition requests"),
    4: ("🛰️ ", "High-Res Plume Imaging",   "CarbonMapper STAC API — exact plume geometry & emission rates"),
    5: ("🏭", "Infrastructure Attribution","Haversine spatial join → attribute each plume to a facility"),
    6: ("⚛️ ", "Plume Inversion (PyTorch)","Gaussian dispersion inversion with wind data → kg/hr"),
    7: ("📋", "Autonomous Audit Reports",  "LangChain + Ollama compliance officer generates regulatory filings"),
}

def _step_hdr(n, run_pk):
    import time
    icon, short, desc = _STEP_META[n]
    W = 70
    print(_pc("═" * W, _C.BLUE))
    print(_pc(f"  [Run #{run_pk}]  STEP {n}/7  {icon}  {short}", _C.BOLD + _C.WHITE))
    print(_pc(f"  {desc}", _C.DIM + _C.CYAN))
    print(_pc("═" * W, _C.BLUE))
    return time.time()

def _step_done(t0, label=""):
    import time
    elapsed = time.time() - t0
    tag = f" — {label}" if label else ""
    print(_pc(f"\n  ✔  Done{tag}  [{elapsed:.2f}s]\n", _C.GREEN))

def _hdiv(c="─", w=66): print(f"  {_C.DIM}{c*w}{_C.RESET}")


def _run_pipeline_background(run_pk, mode, use_llm):
    """Execute the full pipeline in a background thread with rich terminal output."""
    import time
    import numpy as np
    from django.utils import timezone as tz

    run = PipelineRun.objects.get(pk=run_pk)
    pipeline_start = time.time()
    W = 70

    # ── Master header ────────────────────────────────────────────────────
    print()
    print(_pc("█" * W, _C.CYAN))
    print(_pc("█" + " " * (W-2) + "█", _C.CYAN))
    title = f"🛰️   METHANE SHADOW HUNTER  —  API-TRIGGERED RUN  #{run_pk}"
    pad = max(0, (W - 2 - len(title)) // 2)
    print(_pc("█" + " "*pad + title + " "*(W-2-pad-len(title)) + "█", _C.BOLD + _C.CYAN))
    print(_pc("█" + " " * (W-2) + "█", _C.CYAN))
    print(_pc("█" * W, _C.CYAN))
    mode_s = _pc("OFFLINE (bundled CSV)", _C.YELLOW) if mode == "demo" else _pc("LIVE (GEE + APIs)", _C.GREEN)
    llm_s  = _pc("Enabled", _C.GREEN) if use_llm else _pc("Disabled", _C.YELLOW)
    print(f"\n  {_C.BOLD}Mode   :{_C.RESET} {mode_s}")
    print(f"  {_C.BOLD}LLM    :{_C.RESET} {llm_s}")
    print(f"  {_C.BOLD}Started:{_C.RESET} {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}\n")

    try:
        project_root = str(settings.PROJECT_ROOT)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        from src.config import config
        from src.data.sentinel5p import Sentinel5PClient
        from src.data.carbonmapper import CarbonMapperClient
        from src.data.infrastructure import InfrastructureDB
        from src.fusion.hotspot_detector import HotspotDetector
        from src.fusion.tasking_simulator import TaskingSimulator
        from src.fusion.spatial_join import SpatialJoiner
        from src.plume.inversion import PlumeInverter
        from src.plume.wind import WindField

        use_demo = (mode == 'demo')

        # ════════════════════════════════════════════════════════════════
        # STEP 1 — Sentinel-5P
        # ════════════════════════════════════════════════════════════════
        t0 = _step_hdr(1, run_pk)
        s5p = Sentinel5PClient()
        if use_demo:
            print(_inf("Source  : models/dataset/India_Methane_Hotspots.csv"))
            print(_inf("Loading bundled 30-day TROPOMI CH4 mosaic …"))
            hotspots_df = s5p.load_hotspots_csv()
            stats = s5p.get_summary_stats()
        else:
            print(_inf("Source  : Google Earth Engine  COPERNICUS/S5P/OFFL/L3_CH4"))
            print(_inf("Querying GEE for last 30 days …"))
            hotspots_df = s5p.fetch_hotspots_gee(bbox=config.aoi_bbox, days=30)
            stats = s5p.get_summary_stats_from_df(hotspots_df)

        run.total_hotspots = stats['total_hotspots']
        run.save(update_fields=['total_hotspots'])
        _store_raw_hotspots(hotspots_df)

        _hdiv()
        print(_ok(f"Loaded  {stats['total_hotspots']} hotspot locations"))
        _hdiv()
        sc, mc, lc = stats['severe_count'], stats['moderate_count'], stats['low_count']
        print(f"     Severity  :  "
              f"{_C.RED}Severe {sc:>3}{_C.RESET}  │  "
              f"{_C.YELLOW}Moderate {mc:>3}{_C.RESET}  │  "
              f"{_C.DIM}Low {lc:>3}{_C.RESET}")
        print(_dat(f"Max CH4 count  : {stats['max_count']}"))
        print(_dat(f"Lon coverage   : {stats['lon_range'][0]:.2f}° → {stats['lon_range'][1]:.2f}°"))
        print(_dat(f"Lat coverage   : {stats['lat_range'][0]:.2f}° → {stats['lat_range'][1]:.2f}°"))
        if not hotspots_df.empty and 'count' in hotspots_df.columns:
            _hdiv("·")
            print(_dat("Top 3 hotspot rows (by CH4 count):"))
            sample = hotspots_df.nlargest(3, 'count')
            print(_dat(f"  {'Lat':>10}  {'Lon':>11}  {'Count':>7}  {'Severity'}"))
            for _, r in sample.iterrows():
                print(_dat(f"  {r['latitude']:>10.4f}  {r['longitude']:>11.4f}  {int(r['count']):>7}  {r.get('severity','')}"))
        _step_done(t0, f"{stats['total_hotspots']} hotspots loaded")

        # ════════════════════════════════════════════════════════════════
        # STEP 2 — Anomaly Detection
        # ════════════════════════════════════════════════════════════════
        t0 = _step_hdr(2, run_pk)
        sigma = config.hotspot_threshold_sigma
        print(_inf(f"Algorithm : Z-score threshold  σ = {sigma}"))
        print(_inf(f"Strategy  : Flag pixels > (mean + {sigma}×std) of CH4 count"))
        print(_inf("Running detection …"))
        detector   = HotspotDetector(threshold_sigma=sigma)
        detected   = detector.detect(hotspots_df)
        candidates = detector.get_tasking_candidates(detected)
        det_sum    = detector.summary(detected)
        run.detected_hotspots_count = len(candidates)
        run.save(update_fields=['detected_hotspots_count'])
        _store_detected_hotspots(detected, run)

        _hdiv()
        print(_ok(f"Threshold passed  : {det_sum['above_threshold']} / {det_sum['total_analyzed']} points"))
        _hdiv()
        print(_dat(f"Priority 1 — CRITICAL  : {det_sum['priority_1_critical']}"))
        print(_dat(f"Priority 2 — HIGH      : {det_sum['priority_2_high']}"))
        print(_dat(f"Max anomaly score      : {det_sum['max_anomaly_score']:.4f} σ"))
        print(_dat(f"Tasking candidates     : {len(candidates)}"))
        if candidates:
            _hdiv("·")
            print(_dat("Top 5 candidates (by anomaly score):"))
            print(_dat(f"  {'#':<4} {'Lat':>10} {'Lon':>11} {'Score':>8} {'Severity'}"))
            print(_dat(f"  {'─'*4} {'─'*10} {'─'*11} {'─'*8} {'─'*10}"))
            for i, h in enumerate(candidates[:5], 1):
                sc = _C.RED if h.severity=="Severe" else (_C.YELLOW if h.severity=="Moderate" else _C.DIM)
                print(_dat(f"  {i:<4} {h.latitude:>10.4f} {h.longitude:>11.4f} {h.anomaly_score:>8.4f} "
                           f"{sc}{h.severity}{_C.RESET}"))
        _step_done(t0, f"{det_sum['above_threshold']} super-emitter candidates")

        # ════════════════════════════════════════════════════════════════
        # STEP 3 — Satellite Tasking
        # ════════════════════════════════════════════════════════════════
        t0 = _step_hdr(3, run_pk)
        print(_inf("Evaluating candidates against tasking criteria …"))
        print(_inf("Satellites available: CarbonMapper-Tanager, GHGSat, PRISMA"))
        tasking       = TaskingSimulator()
        requests_list = tasking.create_tasking_requests(candidates, max_requests=15)
        task_sum      = tasking.summary()
        _store_tasking_requests(requests_list, run)

        _hdiv()
        print(_ok(f"Tasking requests created  : {task_sum['total_requests']}"))
        _hdiv()
        for sat, cnt in task_sum["by_satellite"].items():
            if cnt > 0:
                bar = "█" * cnt
                print(_dat(f"  {sat:<30}  {_C.CYAN}{bar}{_C.RESET}  {cnt}"))
        if requests_list:
            _hdiv("·")
            print(_dat("First 3 requests:"))
            for r in requests_list[:3]:
                coords = f"({getattr(r,'latitude',0):.4f}, {getattr(r,'longitude',0):.4f})"
                print(_dat(f"  {getattr(r,'satellite','—'):<30} Pri:{getattr(r,'priority','—')}  {coords}"))
        _step_done(t0, f"{task_sum['total_requests']} acquisitions queued")

        # ════════════════════════════════════════════════════════════════
        # STEP 4 — CarbonMapper Plumes
        # ════════════════════════════════════════════════════════════════
        t0 = _step_hdr(4, run_pk)
        cm = CarbonMapperClient()
        hotspot_coords = [(h.latitude, h.longitude) for h in candidates]

        if use_demo:
            print(_inf("Source  : Synthetic high-res plumes  (log-normal  μ=3.9 σ=1.0)"))
            print(_inf("Jitter  : ±0.005° spatial noise on hotspot centroids"))
            print(_inf("Generating plumes …"))
            plumes = cm.generate_synthetic_plumes(hotspot_coords)
            print(_ok(f"Generated {len(plumes)} modelled plumes"))
        else:
            from datetime import timedelta
            end_date   = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            print(_inf(f"Querying CarbonMapper STAC  {start_date} → {end_date}"))
            plumes = cm.search_plumes(bbox=config.aoi_bbox, date_start=start_date, date_end=end_date)
            if not plumes:
                print(_warn("STAC returned 0 results (tasking lag). Falling back to synthetic."))
                plumes = cm.generate_synthetic_plumes(hotspot_coords)
                print(_ok(f"Generated {len(plumes)} modelled plumes (fallback)"))
            else:
                print(_ok(f"Retrieved {len(plumes)} plumes from CarbonMapper STAC API"))

        run.plumes_count = len(plumes)
        run.save(update_fields=['plumes_count'])
        _store_plumes(plumes, run, is_synthetic=use_demo)

        plume_df = cm.plumes_to_dataframe(plumes)
        if not plume_df.empty and 'emission_rate_kg_hr' in plume_df.columns:
            rates = plume_df['emission_rate_kg_hr']
            _hdiv()
            print(_dat(f"Emission range  : {rates.min():.1f} – {rates.max():.1f} kg/hr"))
            print(_dat(f"Mean emission   : {rates.mean():.1f} kg/hr"))
            print(_dat(f"Median emission : {rates.median():.1f} kg/hr"))
            print(_dat(f"Std deviation   : {rates.std():.1f} kg/hr"))
            _hdiv("·")
            print(_dat("Top 5 plumes by emission rate:"))
            print(_dat(f"  {'ID':<12} {'Lat':>9} {'Lon':>10} {'kg/hr':>8} {'Length(m)':>10} {'Quality'}"))
            print(_dat(f"  {'─'*12} {'─'*9} {'─'*10} {'─'*8} {'─'*10} {'─'*8}"))
            for _, row in plume_df.nlargest(5, 'emission_rate_kg_hr').iterrows():
                qc = _C.RED if row['emission_rate_kg_hr'] > 200 else (_C.YELLOW if row['emission_rate_kg_hr'] > 80 else _C.DIM)
                print(_dat(f"  {str(row['plume_id']):<12} {row['latitude']:>9.4f} {row['longitude']:>10.4f} "
                           f"{qc}{row['emission_rate_kg_hr']:>8.1f}{_C.RESET} "
                           f"{row['plume_length_m']:>10.0f} {row['quality_flag']}"))
        _step_done(t0, f"{len(plumes)} plumes characterised")

        # ════════════════════════════════════════════════════════════════
        # STEP 5 — Infrastructure Attribution
        # ════════════════════════════════════════════════════════════════
        t0 = _step_hdr(5, run_pk)
        print(_inf(f"Join algorithm : Haversine distance ≤ {config.spatial_join_radius_km} km"))
        print(_inf("Loading facilities and computing nearest-neighbour distances …"))
        infra      = InfrastructureDB(data_path=config.dataset_dir / "demo_industries.csv")
        facilities = infra.load_facilities()
        joiner     = SpatialJoiner(radius_km=config.spatial_join_radius_km)

        fac_types = {}
        for f in facilities:
            fac_types[f.facility_type] = fac_types.get(f.facility_type, 0) + 1
        print(_ok(f"Loaded {len(facilities)} infrastructure facilities"))
        _hdiv("·")
        print(_dat("Facility type breakdown:"))
        for ft, cnt in sorted(fac_types.items(), key=lambda x: -x[1]):
            print(_dat(f"  {ft:<16}  {_C.CYAN}{'▪'*min(cnt,20)}{_C.RESET}  {cnt}"))

        print(_inf("Joining plumes → facilities …"))
        attributions = joiner.join(plumes, facilities)
        metrics      = joiner.metrics(attributions)
        run.attributions_count = len(attributions)
        run.save(update_fields=['attributions_count'])
        _store_attributions(attributions, run)

        _hdiv()
        if metrics['total_attributed'] > 0:
            print(_ok(f"Attributed  {metrics['total_attributed']} / {len(plumes)} plumes  →  facilities"))
            _hdiv()
            print(_dat(f"Mean pinpoint accuracy  : {metrics['mean_pinpoint_accuracy_m']:.0f} m"))
            print(_dat(f"≤ 500 m accuracy        : {metrics['pct_within_500m']:.1f}%"))
            print(_dat(f"≤ 1 km accuracy         : {metrics['pct_within_1km']:.1f}%"))
            print(_dat(f"High confidence joins   : {metrics['high_confidence_pct']:.1f}%"))
            print(_dat(f"Total attributed load   : {metrics['total_emission_rate_kg_hr']:.1f} kg/hr"))
            _hdiv("·")
            print(_dat("Full attribution table:"))
            print(_dat(f"  {'Facility':<40} {'Operator':<22} {'Dist(m)':>8} {'kg/hr':>8} {'Conf'}"))
            print(_dat(f"  {'─'*40} {'─'*22} {'─'*8} {'─'*8} {'─'*6}"))
            for a in attributions:
                cc = _C.GREEN if a.confidence=='high' else (_C.YELLOW if a.confidence=='medium' else _C.DIM)
                rc = _C.RED   if a.emission_rate_kg_hr > 150 else (_C.YELLOW if a.emission_rate_kg_hr > 60 else _C.RESET)
                print(_dat(f"  {a.facility_name[:40]:<40} {a.operator[:22]:<22} "
                           f"{a.pinpoint_accuracy_m:>8.0f} "
                           f"{rc}{a.emission_rate_kg_hr:>8.1f}{_C.RESET} "
                           f"{cc}{a.confidence}{_C.RESET}"))
        else:
            print(_warn(f"0 plumes attributed (no facility within {config.spatial_join_radius_km} km)"))
        _step_done(t0, f"{metrics['total_attributed']} facility attributions")

        # ════════════════════════════════════════════════════════════════
        # STEP 6 — Plume Inversion
        # ════════════════════════════════════════════════════════════════
        t0 = _step_hdr(6, run_pk)
        wind_src = "Open-Meteo live API" if not use_demo else "synthetic wind field (offline)"
        print(_inf("Physics model  : Gaussian plume dispersion (Pasquill–Gifford class D)"))
        print(_inf(f"Wind data      : {wind_src}"))
        print(_inf("Optimisation   : PyTorch gradient-based inversion"))
        print(_inf("Running inversion for top 5 attributed emitters …"))
        _hdiv()

        inverter     = PlumeInverter(stability_class="D")
        wind         = WindField(use_live=not use_demo)
        top_emitters = sorted(attributions, key=lambda a: a.emission_rate_kg_hr, reverse=True)[:5]

        # DB storage (silent)
        _run_and_store_inversions(top_emitters, inverter, wind, run)

        # Terminal display loop (always runs, independent of DB storage)
        inversion_results = []
        for i, attr in enumerate(top_emitters, 1):
            wind_data   = wind.get_wind(attr.plume_lat, attr.plume_lon)
            true_Q_kg_s = attr.emission_rate_kg_hr / 3600
            synth = inverter.create_synthetic_observation(
                true_Q_kg_s=true_Q_kg_s,
                wind_speed=wind_data.speed_ms,
                stability_class=wind_data.stability_class,
                n_receptors=200,
                domain_m=3000,
                noise_level=0.05,
            )
            result = inverter.invert(
                observed_concentrations=synth["observed_concentrations"],
                receptor_x=synth["receptor_x"],
                receptor_y=synth["receptor_y"],
                receptor_z=synth["receptor_z"],
                wind_speed=wind_data.speed_ms,
                initial_Q=0.01,
                source_height=5.0,
                true_Q_kg_hr=synth["true_Q_kg_hr"],
            )
            inversion_results.append(result)
            conv  = _pc("✔ converged",     _C.GREEN) if result.converged else _pc("✗ not converged", _C.RED)
            ec    = (_C.GREEN if result.error_pct < 15 else (_C.YELLOW if result.error_pct < 30 else _C.RED))
            print(f"  {_C.BOLD}[{i}]{_C.RESET} {attr.facility_name[:38]:<38}")
            print(_dat(f"  True rate  : {synth['true_Q_kg_hr']:>8.2f} kg/hr"))
            print(_dat(f"  Estimated  : {result.estimated_Q_kg_hr:>8.2f} kg/hr"
                       f"   95% CI [{result.confidence_interval[0]:.1f}, {result.confidence_interval[1]:.1f}]"))
            print(_dat(f"  Error      : {ec}{result.error_pct:.2f}%{_C.RESET}"
                       f"   Wind: {wind_data.speed_ms:.1f} m/s  Dir: {wind_data.direction_deg:.0f}°"
                       f"   Status: {conv}"))
            if i < len(top_emitters):
                _hdiv("·")

        if inversion_results:
            errors = [r.error_pct for r in inversion_results if r.error_pct is not None]
            if errors:
                _hdiv()
                me = np.mean(errors)
                ec = _C.GREEN if me < 15 else (_C.YELLOW if me < 30 else _C.RED)
                print(_ok(f"Mean inversion error : {ec}{me:.2f}%{_C.RESET}"))
        _step_done(t0, f"{len(top_emitters)} emission rates solved")

        # ════════════════════════════════════════════════════════════════
        # STEP 7 — Compliance Reports
        # ════════════════════════════════════════════════════════════════
        t0 = _step_hdr(7, run_pk)
        if use_llm:
            print(_inf(f"Agent model    : {config.ollama_model}  @  {config.ollama_base_url}"))
            print(_inf("Agent role     : Regulatory compliance officer"))
            print(_inf("Output format  : Markdown (exec summary + risk level + remediation)"))
            print(_inf("Generating reports for top 3 attributed emitters …"))
            try:
                from src.agent.reporting_agent import ComplianceAuditAgent
                agent          = ComplianceAuditAgent(model=config.ollama_model, base_url=config.ollama_base_url)
                top_for_report = sorted(attributions, key=lambda a: a.emission_rate_kg_hr, reverse=True)[:3]
                plume_map      = {p.plume_id: p for p in plumes}
                reports        = agent.generate_batch_reports(top_for_report, plume_map)
                run.reports_count = len(reports)
                run.save(update_fields=['reports_count'])
                _store_reports(reports, run)
                _hdiv()
                for rpt in reports:
                    rc = (_C.RED    if 'CRITICAL' in rpt.risk_level.upper() else
                          _C.YELLOW if 'HIGH'     in rpt.risk_level.upper() else _C.GREEN)
                    print(_ok(f"{rpt.report_id}"))
                    print(_dat(f"  Facility   : {rpt.facility_name}"))
                    print(_dat(f"  Risk level : {rc}{rpt.risk_level}{_C.RESET}"))
                    _hdiv("·")
            except Exception as e:
                print(_warn(f"LLM report generation failed: {e}"))
                run.error_message += f"LLM report generation failed: {str(e)}\n"
                run.save(update_fields=['error_message'])
        else:
            print(_warn("LLM disabled — skipping autonomous report generation."))
            run.reports_count = 0
        _step_done(t0, f"{run.reports_count} reports written")

        # ════════════════════════════════════════════════════════════════
        # FINAL SUMMARY
        # ════════════════════════════════════════════════════════════════
        total_elapsed = time.time() - pipeline_start
        run.status       = 'completed'
        run.completed_at = tz.now()
        run.save(update_fields=['status', 'completed_at'])

        print(_pc("═" * W, _C.CYAN))
        print(_pc(f"  🏁  PIPELINE COMPLETE  —  Run #{run_pk}", _C.BOLD + _C.WHITE))
        print(_pc("═" * W, _C.CYAN))
        def _sr(lbl, val, col=_C.WHITE): print(f"  {_C.DIM}{lbl:<40}{_C.RESET}  {col}{val}{_C.RESET}")
        _sr("Sentinel-5P hotspots analysed",  stats['total_hotspots'])
        _sr("Super-emitter candidates",        det_sum['above_threshold'],              _C.YELLOW)
        _sr("Satellite tasking requests",       task_sum['total_requests'],              _C.CYAN)
        _sr("Plumes characterised",             len(plumes),                             _C.CYAN)
        _sr("Attributed to facilities",         metrics['total_attributed'],
            _C.GREEN if metrics['total_attributed'] > 0 else _C.RED)
        if metrics['total_attributed'] > 0:
            _sr("Total attributed emission load", f"{metrics['total_emission_rate_kg_hr']:.1f} kg/hr", _C.RED)
            _sr("Mean pinpoint accuracy",         f"{metrics['mean_pinpoint_accuracy_m']:.0f} m",      _C.GREEN)
        _sr("Audit reports generated",          run.reports_count,                       _C.GREEN)
        _sr("Total pipeline runtime",           f"{total_elapsed:.2f} s",                _C.CYAN)
        print(_pc("═" * W, _C.CYAN))
        print()

    except Exception as e:
        run.status        = 'failed'
        run.error_message = traceback.format_exc()
        run.completed_at  = timezone.now()
        run.save(update_fields=['status', 'error_message', 'completed_at'])
        print(_pc(f"\n  ✗  PIPELINE FAILED (Run #{run_pk}): {e}\n", _C.RED + _C.BOLD))
        print(_pc(traceback.format_exc(), _C.DIM + _C.RED))




# ─── Dashboard Summary ────────────────────────────────────────────────────

class DashboardSummaryView(APIView):
    """
    GET /api/dashboard/summary/

    Aggregated metrics for the React dashboard.
    """

    def get(self, request):
        # Facility stats
        total_facilities = Facility.objects.count()
        type_dist = dict(
            Facility.objects.values_list('type')
            .annotate(c=Count('id'))
            .values_list('type', 'c')
        )
        operator_dist = dict(
            Facility.objects.values_list('operator')
            .annotate(c=Count('id'))
            .values_list('operator', 'c')
        )

        # Hotspot stats
        total_hotspots = MethaneHotspot.objects.count()
        total_detected = DetectedHotspot.objects.count()
        critical_hotspots = DetectedHotspot.objects.filter(priority=1).count()

        # Plume & attribution stats
        total_plumes = PlumeObservation.objects.count()
        total_attributions = AttributedEmission.objects.count()
        high_conf = AttributedEmission.objects.filter(confidence='high').count()

        # Reports
        total_reports = AuditReport.objects.count()
        recent_reports = AuditReport.objects.select_related('facility').order_by('-generated_at')[:5]

        # Top emitting facilities
        top_emitter_ids = (
            AttributedEmission.objects
            .values('facility')
            .annotate(total_emission=Sum('emission_rate_kg_hr'))
            .order_by('-total_emission')[:10]
        )
        top_facility_ids = [e['facility'] for e in top_emitter_ids]
        top_emitters = Facility.objects.filter(id__in=top_facility_ids)

        # Pipeline runs
        total_runs = PipelineRun.objects.count()
        last_run = PipelineRun.objects.order_by('-started_at').first()

        # Tasking requests
        total_tasking = TaskingRequest.objects.count()

        # Severity breakdown derived from consistent priority field
        # priority 1=Critical, 2=High, 3=Moderate
        severity_dist = {
            'Critical': DetectedHotspot.objects.filter(priority=1).count(),
            'High':     DetectedHotspot.objects.filter(priority=2).count(),
            'Medium':   DetectedHotspot.objects.filter(priority=3).count(),
            'Low':      0,  # reserved for future lower-priority tier
        }

        return Response({
            'total_facilities': total_facilities,
            'total_hotspots': total_hotspots,
            'total_detected': total_detected,
            'total_plumes': total_plumes,
            'total_attributions': total_attributions,
            'total_reports': total_reports,
            'total_pipeline_runs': total_runs,
            'total_tasking_requests': total_tasking,
            'critical_hotspots': critical_hotspots,
            'high_confidence_attributions': high_conf,
            'top_emitters': FacilityListSerializer(top_emitters, many=True).data,
            'recent_reports': AuditReportListSerializer(recent_reports, many=True).data,
            'facility_type_distribution': type_dist,
            'operator_distribution': operator_dist,
            'severity_distribution': severity_dist,
            'last_pipeline_run': {
                'id': last_run.pk,
                'status': last_run.status,
                'started_at': last_run.started_at.isoformat(),
                'completed_at': last_run.completed_at.isoformat() if last_run.completed_at else None,
            } if last_run else None,
        })


# ─── Dashboard Trend ─────────────────────────────────────────────────────

class DashboardTrendView(APIView):
    """
    GET /api/dashboard/trend/

    Returns last-12-months monthly emission and detection counts.
    """

    def get(self, request):
        from datetime import timedelta
        from django.db.models.functions import TruncMonth

        now = timezone.now()
        start = now - timedelta(days=365)

        # Monthly total attributed emissions (kg/hr sum) and attribution count
        monthly_emissions = (
            AttributedEmission.objects
            .filter(attributed_at__gte=start)
            .annotate(month=TruncMonth('attributed_at'))
            .values('month')
            .annotate(total=Sum('emission_rate_kg_hr'), count=Count('id'))
            .order_by('month')
        )

        # Monthly detected hotspot counts
        monthly_hotspots = (
            DetectedHotspot.objects
            .filter(detected_at__gte=start)
            .annotate(month=TruncMonth('detected_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        emission_map = {
            row['month'].strftime('%Y-%m'): row
            for row in monthly_emissions
        }
        hotspot_map = {
            row['month'].strftime('%Y-%m'): row['count']
            for row in monthly_hotspots
        }

        all_months = sorted(set(emission_map.keys()) | set(hotspot_map.keys()))

        result = []
        for key in all_months:
            e = emission_map.get(key, {})
            result.append({
                'month': datetime.strptime(key, '%Y-%m').strftime('%b %Y'),
                'emissions': round(float(e.get('total') or 0), 2),
                'detected': hotspot_map.get(key, 0),
            })

        return Response(result)


# ─── GeoJSON Export Endpoints ─────────────────────────────────────────────

@api_view(['GET'])
def facilities_geojson(request):
    """Export facilities as GeoJSON FeatureCollection."""
    facilities = Facility.objects.all()
    features = []
    for f in facilities:
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(f.longitude), float(f.latitude)],
            },
            'properties': {
                'id': f.pk,
                'facility_id': f.facility_id,
                'name': f.name,
                'type': f.type,
                'operator': f.operator,
                'status': f.status,
            },
        })
    return Response({
        'type': 'FeatureCollection',
        'features': features,
    })


@api_view(['GET'])
def hotspots_geojson(request):
    """Export methane hotspots as GeoJSON FeatureCollection."""
    hotspots = MethaneHotspot.objects.all()
    features = []
    for h in hotspots:
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(h.longitude), float(h.latitude)],
            },
            'properties': {
                'id': h.pk,
                'system_index': h.system_index,
                'count': h.count,
                'severity': h.severity,
            },
        })
    return Response({
        'type': 'FeatureCollection',
        'features': features,
    })


@api_view(['GET'])
def attributions_geojson(request):
    """Export attributed emissions as GeoJSON with lines from plume→facility."""
    attributions = AttributedEmission.objects.select_related('facility', 'plume').all()
    features = []
    for a in attributions:
        # Plume point
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(a.plume.longitude), float(a.plume.latitude)],
            },
            'properties': {
                'type': 'plume',
                'plume_id': a.plume.plume_id,
                'emission_rate_kg_hr': a.emission_rate_kg_hr,
                'confidence': a.confidence,
            },
        })
        # Line from plume to facility
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': [
                    [float(a.plume.longitude), float(a.plume.latitude)],
                    [float(a.facility.longitude), float(a.facility.latitude)],
                ],
            },
            'properties': {
                'type': 'attribution_line',
                'distance_km': a.distance_km,
                'confidence': a.confidence,
                'facility_name': a.facility.name,
            },
        })
    return Response({
        'type': 'FeatureCollection',
        'features': features,
    })


# ─── DB-based Heatmap Fallback ────────────────────────────────────────────

@api_view(['GET'])
def heatmap_fallback(request):
    """
    Return heatmap-ready [lat, lng, intensity] points derived from existing
    database records (MethaneHotspot + DetectedHotspot + PlumeObservation).
    Used when GEE is unavailable.

    Returns:
        {
            "points":     [[lat, lng, intensity], ...],
            "stats":      { mean, std, min, max, count },
            "source":     "database",
            "raw_points": [[lat, lng, raw_value], ...],
        }
    """
    import numpy as np

    print('\n[DB-FALLBACK] ─────────────────────────────────────────')
    print('[DB-FALLBACK] heatmap_fallback called')

    raw_points = []  # [[lat, lng, raw_value], ...]

    # 1) MethaneHotspot.count → use as raw intensity proxy
    methane_qs = list(MethaneHotspot.objects.values_list('latitude', 'longitude', 'count'))
    print(f'[DB-FALLBACK] MethaneHotspot total rows   : {len(methane_qs)}')
    methane_added = 0
    for h in methane_qs:
        if h[0] is not None and h[1] is not None and h[2] is not None:
            raw_points.append([float(h[0]), float(h[1]), float(h[2])])
            methane_added += 1
    print(f'[DB-FALLBACK] MethaneHotspot valid points : {methane_added}')

    # 2) DetectedHotspot.ch4_count
    detected_qs = list(DetectedHotspot.objects.values_list('latitude', 'longitude', 'ch4_count'))
    print(f'[DB-FALLBACK] DetectedHotspot total rows  : {len(detected_qs)}')
    detected_added = 0
    for d in detected_qs:
        if d[0] is not None and d[1] is not None and d[2] is not None:
            raw_points.append([float(d[0]), float(d[1]), float(d[2])])
            detected_added += 1
    print(f'[DB-FALLBACK] DetectedHotspot valid points: {detected_added}')

    # 3) PlumeObservation.emission_rate_kg_hr (scaled to same order)
    plumes = list(PlumeObservation.objects.values_list(
        'latitude', 'longitude', 'emission_rate_kg_hr'
    ))
    print(f'[DB-FALLBACK] PlumeObservation total rows : {len(plumes)}')
    plume_added = 0
    if plumes:
        # Scale plume emission rates to roughly match hotspot counts
        max_count = max((p[2] for p in raw_points), default=1) if raw_points else 1
        max_plume = max((p[2] for p in plumes if p[2]), default=1)
        scale = max_count / max_plume if max_plume else 1
        print(f'[DB-FALLBACK] Plume scale factor          : {scale:.6f}')
        for p in plumes:
            if p[0] is not None and p[1] is not None and p[2] is not None:
                raw_points.append([float(p[0]), float(p[1]), float(p[2]) * scale])
                plume_added += 1
    print(f'[DB-FALLBACK] PlumeObservation valid pts  : {plume_added}')
    print(f'[DB-FALLBACK] Total raw_points collected  : {len(raw_points)}')

    if not raw_points:
        print('[DB-FALLBACK] ✗ No raw points — returning empty response')
        print('[DB-FALLBACK] ─────────────────────────────────────────\n')
        return Response({
            'points': [], 'stats': {}, 'raw_points': [], 'source': 'database',
        })

    values = np.array([p[2] for p in raw_points])
    v_min = float(np.nanmin(values))
    v_max = float(np.nanmax(values))
    v_mean = float(np.nanmean(values))
    v_std = float(np.nanstd(values))
    spread = v_max - v_min if v_max > v_min else 1.0

    # Normalise to 0-1
    points = [[p[0], p[1], (p[2] - v_min) / spread] for p in raw_points]

    print(f'[DB-FALLBACK] Stats — min:{v_min:.2f}  max:{v_max:.2f}  mean:{v_mean:.2f}  std:{v_std:.2f}')
    print(f'[DB-FALLBACK] Normalised points count     : {len(points)}')
    if points:
        print(f'[DB-FALLBACK] Sample (first 3 norm pts)   : {points[:3]}')
    print('[DB-FALLBACK] ✔ Returning response')
    print('[DB-FALLBACK] ─────────────────────────────────────────\n')

    return Response({
        'points': points,
        'raw_points': raw_points,
        'stats': {
            'mean': round(v_mean, 2),
            'std': round(v_std, 2),
            'min': round(v_min, 2),
            'max': round(v_max, 2),
            'count': len(values),
        },
        'source': 'database',
    })


# ─── Google Earth Engine Endpoints ─────────────────────────────────────────

@api_view(['GET'])
def gee_ch4_tiles(request):
    """
    Return a GEE-generated tile URL for Sentinel-5P CH4 heatmap overlay.
    Query params:
        days  – number of days to average (default 30)
    """
    days = int(request.query_params.get('days', 30))

    print(f'\n[GEE-TILES] ─────────────────────────────────────────')
    print(f'[GEE-TILES] gee_ch4_tiles called  days={days}')
    try:
        from .gee_service import get_tile_url
        result = get_tile_url(days=days)
        print(f'[GEE-TILES] ✔ tile_url generated: {str(result.get("tile_url", ""))[:80]}...')
        print('[GEE-TILES] ─────────────────────────────────────────\n')
        return Response(result)
    except Exception as e:
        print(f'[GEE-TILES] ✗ FAILED  {type(e).__name__}: {e}')
        print('[GEE-TILES] ─────────────────────────────────────────\n')
        return Response(
            {'error': str(e), 'detail': 'GEE tile generation failed. Check Earth Engine authentication.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(['GET'])
def gee_ch4_heatmap(request):
    """
    Return sampled CH4 points as [lat, lng, intensity] for leaflet.heat.
    Query params:
        days       – number of days to average (default 30)
        num_points – max sample points (default 1000)
        scale      – sampling resolution in metres (default 20000)
    """
    import logging as _logging
    _log = _logging.getLogger(__name__)

    days = int(request.query_params.get('days', 30))
    num_points = int(request.query_params.get('num_points', 1000))
    scale = int(request.query_params.get('scale', 20000))

    print(f'\n[GEE-HEATMAP] ───────────────────────────────────────')
    print(f'[GEE-HEATMAP] gee_ch4_heatmap called')
    print(f'[GEE-HEATMAP] Input params  days={days}  num_points={num_points}  scale={scale}')

    try:
        from .gee_service import get_heatmap_points
        result = get_heatmap_points(days=days, num_points=num_points, scale=scale)
        n_pts = len(result.get('points', []))
        _log.info('[GEE] ch4-heatmap: returned %d points', n_pts)
        print(f'[GEE-HEATMAP] ✔ GEE returned {n_pts} points')
        print(f'[GEE-HEATMAP] Stats  : {result.get("stats")}')
        if result.get('points'):
            print(f'[GEE-HEATMAP] Sample (first 3): {result["points"][:3]}')
        print('[GEE-HEATMAP] ───────────────────────────────────────\n')
        return Response(result)
    except TimeoutError as e:
        _log.warning('[GEE] ch4-heatmap timed out: %s', e)
        print(f'[GEE-HEATMAP] ✗ TIMEOUT after {e}')
        print('[GEE-HEATMAP] ───────────────────────────────────────\n')
        return Response(
            {'error': 'timeout', 'detail': str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        _log.warning('[GEE] ch4-heatmap failed (%s): %s', type(e).__name__, e)
        import traceback as _tb
        print(f'[GEE-HEATMAP] ✗ EXCEPTION  {type(e).__name__}: {e}')
        print('[GEE-HEATMAP] Traceback:')
        print(_tb.format_exc())
        print('[GEE-HEATMAP] ───────────────────────────────────────\n')
        return Response(
            {'error': type(e).__name__, 'detail': str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(['GET'])
def gee_ch4_hotspots(request):
    """
    Detect CH4 anomaly hotspots from Sentinel-5P TROPOMI for an explicit date range.

    Query params:
        start_date – YYYY-MM-DD  (default: 7 days ago)
        end_date   – YYYY-MM-DD  (default: today)
        num_points – max sample points (default 1000)
        scale      – sampling resolution in metres (default 20000)

    Returns:
        {
            "hotspots": [ { id, latitude, longitude, ch4_ppb, anomaly_score, severity, priority, detected_at }, … ],
            "stats":    { mean, std, min, max, count, total_sampled },
            "tile_url": "https://earthengine.googleapis.com/…" | null,
            "start_date": "YYYY-MM-DD",
            "end_date":   "YYYY-MM-DD",
        }
    """
    from datetime import date, timedelta
    _today = date.today()
    default_start = (_today - timedelta(days=7)).strftime("%Y-%m-%d")
    default_end   = _today.strftime("%Y-%m-%d")

    start_date = request.query_params.get('start_date', default_start)
    end_date   = request.query_params.get('end_date',   default_end)
    num_points = int(request.query_params.get('num_points', 1000))
    scale      = int(request.query_params.get('scale',      20000))

    try:
        from .gee_service import get_hotspots_by_dates
        result = get_hotspots_by_dates(
            start_date=start_date,
            end_date=end_date,
            num_points=num_points,
            scale=scale,
        )
        return Response(result)
    except Exception as e:
        return Response(
            {
                'error':  str(e),
                'detail': (
                    'GEE hotspot query failed. '
                    'Ensure Earth Engine is authenticated and the date range '
                    'falls within the Sentinel-5P TROPOMI archive (after May 2018).'
                ),
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(['GET'])
def gee_company_analysis(request):
    """
    Company-centric CH4 analysis via Google Earth Engine.

    Accepts either a ``facility_id`` (database PK) to auto-resolve coordinates,
    or explicit ``lat`` / ``lng``.  Queries Sentinel-5P TROPOMI data within
    ``radius_km`` of that location for the given date range.

    Query params:
        facility_id – PK of a Facility (optional – overrides lat/lng)
        lat / lng   – centre coordinates (required if no facility_id)
        radius_km   – search radius in km (default 50)
        start_date  – YYYY-MM-DD  (default: 30 days ago)
        end_date    – YYYY-MM-DD  (default: today)
        num_points  – max sample points (default 1000)
        scale       – sampling resolution in metres (default 10000)

    Returns the same structure as ``get_hotspots_by_location`` plus a
    ``facility`` object when resolved from ``facility_id``.
    """
    from datetime import date, timedelta

    _today = date.today()
    default_start = (_today - timedelta(days=30)).strftime("%Y-%m-%d")
    default_end   = _today.strftime("%Y-%m-%d")

    facility_id = request.query_params.get('facility_id')
    lat         = request.query_params.get('lat')
    lng         = request.query_params.get('lng')
    radius_km   = float(request.query_params.get('radius_km', 50))
    start_date  = request.query_params.get('start_date', default_start)
    end_date    = request.query_params.get('end_date',   default_end)
    num_points  = int(request.query_params.get('num_points', 1000))
    scale       = int(request.query_params.get('scale',      10000))

    facility_data = None

    if facility_id:
        try:
            fac = Facility.objects.get(pk=facility_id)
        except Facility.DoesNotExist:
            return Response(
                {'error': f'Facility with id={facility_id} not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        lat = float(fac.latitude)
        lng = float(fac.longitude)
        facility_data = {
            'id':        fac.pk,
            'facility_id': fac.facility_id,
            'name':      fac.name,
            'operator':  fac.operator,
            'type':      fac.type,
            'state':     fac.state,
            'status':    fac.status,
            'latitude':  float(fac.latitude),
            'longitude': float(fac.longitude),
        }
    else:
        if not lat or not lng:
            return Response(
                {'error': 'Provide either facility_id or both lat & lng.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        lat = float(lat)
        lng = float(lng)

    try:
        from .gee_service import get_hotspots_by_location
        result = get_hotspots_by_location(
            center_lat=lat,
            center_lng=lng,
            radius_km=radius_km,
            start_date=start_date,
            end_date=end_date,
            num_points=num_points,
            scale=scale,
        )
        if facility_data:
            result['facility'] = facility_data
        return Response(result)
    except Exception as e:
        return Response(
            {
                'error':  str(e),
                'detail': (
                    'GEE company analysis failed. '
                    'Ensure Earth Engine is authenticated and the date range '
                    'falls within the Sentinel-5P TROPOMI archive (after May 2018).'
                ),
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# ─── Helper functions ─────────────────────────────────────────────────────

def _haversine(lat1, lon1, lat2, lon2):
    """Haversine distance in km."""
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _store_raw_hotspots(hotspots_df):
    """Bulk-insert raw methane hotspots (skip duplicates)."""
    existing = set(MethaneHotspot.objects.values_list('system_index', flat=True))
    objs = []
    for _, row in hotspots_df.iterrows():
        idx = str(row.get('system_index', row.name))
        if idx in existing:
            continue
        objs.append(MethaneHotspot(
            system_index=idx,
            count=int(row['count']),
            label=int(row.get('label', 1)),
            latitude=row['latitude'],
            longitude=row['longitude'],
            severity=row.get('severity', ''),
        ))
    if objs:
        MethaneHotspot.objects.bulk_create(objs, ignore_conflicts=True)


def _store_detected_hotspots(detected, run):
    """Store detected hotspot results."""
    objs = []
    for d in detected:
        if d.requires_highres:
            objs.append(DetectedHotspot(
                hotspot_id=d.hotspot_id,
                latitude=d.latitude,
                longitude=d.longitude,
                ch4_count=d.ch4_count,
                anomaly_score=d.anomaly_score,
                severity=d.severity,
                requires_highres=d.requires_highres,
                priority=d.priority,
                pipeline_run=run,
            ))
    if objs:
        DetectedHotspot.objects.bulk_create(objs, ignore_conflicts=True)


def _store_tasking_requests(requests, run):
    """Store satellite tasking requests."""
    objs = []
    for r in requests:
        objs.append(TaskingRequest(
            request_id=r.request_id,
            satellite=r.satellite,
            latitude=r.latitude,
            longitude=r.longitude,
            priority=r.priority,
            status=r.status,
            pipeline_run=run,
        ))
    if objs:
        TaskingRequest.objects.bulk_create(objs, ignore_conflicts=True)


def _store_plumes(plumes, run, is_synthetic=True):
    """Store plume observations."""
    objs = []
    for p in plumes:
        objs.append(PlumeObservation(
            plume_id=p.plume_id,
            latitude=p.latitude,
            longitude=p.longitude,
            emission_rate_kg_hr=p.emission_rate_kg_hr,
            wind_speed_ms=getattr(p, 'wind_speed_ms', getattr(p, 'wind_speed', 3.0)),
            wind_direction_deg=getattr(p, 'wind_direction_deg', getattr(p, 'wind_direction', 0.0)),
            plume_length_m=getattr(p, 'plume_length_m', None),
            sector=getattr(p, 'sector', ''),
            concentration_ppm=getattr(p, 'concentration_ppm', None),
            is_synthetic=is_synthetic,
            pipeline_run=run,
        ))
    if objs:
        PlumeObservation.objects.bulk_create(objs, ignore_conflicts=True)


def _store_attributions(attributions, run):
    """Store spatial join attributions."""
    for a in attributions:
        # Look up plume and facility in DB
        plume = PlumeObservation.objects.filter(plume_id=a.plume_id).first()
        facility = Facility.objects.filter(facility_id=a.facility_id).first()
        if plume and facility:
            AttributedEmission.objects.create(
                plume=plume,
                facility=facility,
                distance_km=a.distance_km,
                confidence=a.confidence,
                emission_rate_kg_hr=a.emission_rate_kg_hr,
                pipeline_run=run,
            )


def _run_and_store_inversions(top_emitters, inverter, wind, run):
    """Run plume inversion for top emitters and store results."""
    import numpy as np

    for attr in top_emitters:
        try:
            wind_data = wind.get_wind(attr.latitude, attr.longitude)
            Q_true_kg_s = attr.emission_rate_kg_hr / 3600.0  # kg/s

            # Use the inverter's synthetic observation generator
            # This ensures consistent receptor layouts and benefits from all fixes
            synth = inverter.create_synthetic_observation(
                true_Q_kg_s=Q_true_kg_s,
                wind_speed=wind_data.speed_ms,
                stability_class=wind_data.stability_class,
                n_receptors=200,
                domain_m=3000,
                noise_level=0.05,
            )

            # Run inversion (now uses adaptive initial Q, scaled observations, etc.)
            result = inverter.invert(
                observed_concentrations=synth["observed_concentrations"],
                receptor_x=synth["receptor_x"],
                receptor_y=synth["receptor_y"],
                receptor_z=synth["receptor_z"],
                wind_speed=wind_data.speed_ms,
                initial_Q=0.01,  # Will be overridden by adaptive estimation
                source_height=5.0,
                true_Q_kg_hr=attr.emission_rate_kg_hr,
            )

            # Find DB attribution
            plume_obj = PlumeObservation.objects.filter(plume_id=attr.plume_id).first()
            facility_obj = Facility.objects.filter(facility_id=attr.facility_id).first()
            if plume_obj and facility_obj:
                db_attr = AttributedEmission.objects.filter(
                    plume=plume_obj, facility=facility_obj, pipeline_run=run
                ).first()
                if db_attr:
                    InversionResult.objects.create(
                        attribution=db_attr,
                        estimated_q_kg_hr=result.estimated_Q_kg_hr,
                        estimated_q_kg_s=result.estimated_Q_kg_s,
                        true_q_kg_hr=result.true_Q_kg_hr,
                        error_pct=result.error_pct,
                        ci_lower_kg_hr=result.confidence_interval[0],
                        ci_upper_kg_hr=result.confidence_interval[1],
                        final_loss=result.final_loss,
                        n_iterations=result.n_iterations,
                        converged=result.converged,
                        pipeline_run=run,
                    )
        except Exception:
            continue


def _store_reports(reports, run):
    """Store audit reports in DB."""
    import re as _re

    _RISK_MAP = {'CRITICAL': 'CRITICAL', 'HIGH': 'HIGH', 'MEDIUM': 'MEDIUM', 'LOW': 'LOW'}
    _CONF_MAP = {'CRITICAL': 'high', 'HIGH': 'high', 'MEDIUM': 'medium', 'LOW': 'low'}

    for report in reports:
        facility = Facility.objects.filter(facility_id=report.facility_id).first()
        if not facility:
            continue

        # Strip emoji / colour-indicator prefixes from risk_level
        # e.g. "🔴 CRITICAL" → "CRITICAL", "🟠 HIGH" → "HIGH"
        raw_risk    = getattr(report, 'risk_level', 'MEDIUM') or 'MEDIUM'
        clean_risk  = _re.sub(r'[^\w\s]', '', raw_risk).strip().upper()
        risk_level  = next((v for k, v in _RISK_MAP.items() if k in clean_risk), 'MEDIUM')
        confidence  = _CONF_MAP.get(risk_level, 'medium')

        # Full markdown content
        report_markdown = getattr(report, 'report_markdown', '') or ''

        # Executive summary: prefer llm_analysis first paragraph, else first
        # substantial line of the markdown, else empty string
        exec_summary = getattr(report, 'llm_analysis', '') or ''
        if exec_summary:
            exec_summary = exec_summary.split('\n\n')[0].strip()
        if not exec_summary:
            for line in report_markdown.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and len(line) > 40:
                    exec_summary = line
                    break
        exec_summary = exec_summary[:1000]   # stay within TextField comfort zone

        AuditReport.objects.update_or_create(
            report_id=report.report_id,
            defaults={
                'facility':            facility,
                'attribution':         None,
                'emission_rate_kg_hr': report.emission_rate_kg_hr,
                'risk_level':          risk_level,
                'confidence':          confidence,
                'report_markdown':     report_markdown,
                'executive_summary':   exec_summary,
                'pipeline_run':        run,
            },
        )


# ═══════════════════════════════════════════════════════════════════════════
# Authentication Views
# ═══════════════════════════════════════════════════════════════════════════

class RegisterView(APIView):
    """User registration endpoint."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                'message': 'Account created successfully.',
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """User login endpoint."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response(
                {'errors': {'non_field_errors': ['Invalid username or password.']}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response(
                {'errors': {'non_field_errors': ['This account has been deactivated.']}},
                status=status.HTTP_403_FORBIDDEN,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                'message': 'Login successful.',
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
            },
            status=status.HTTP_200_OK,
        )
