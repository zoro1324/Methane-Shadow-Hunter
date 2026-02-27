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

    Runs the methane detection pipeline and stores all results in the DB.
    """

    def post(self, request):
        serializer = PipelineTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mode = serializer.validated_data.get('mode', 'demo')
        use_llm = serializer.validated_data.get('use_llm', False)

        # Create pipeline run record
        run = PipelineRun.objects.create(
            mode=mode,
            use_llm=use_llm,
            status='running',
        )

        try:
            # Add project root to sys.path for src imports
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
            from src.plume.gaussian_plume import GaussianPlumeModel
            from src.plume.inversion import PlumeInverter
            from src.plume.wind import WindField

            use_demo = (mode == 'demo')

            # Step 1: Load Sentinel-5P data
            s5p = Sentinel5PClient()
            if use_demo:
                hotspots_df = s5p.load_hotspots_csv()
            else:
                hotspots_df = s5p.fetch_hotspots_gee(bbox=config.aoi_bbox, days=30)

            stats = s5p.get_summary_stats() if use_demo else s5p.get_summary_stats_from_df(hotspots_df)
            run.total_hotspots = stats['total_hotspots']

            # Store raw hotspots in DB
            _store_raw_hotspots(hotspots_df)

            # Step 2: Detect anomalies
            detector = HotspotDetector(threshold_sigma=config.hotspot_threshold_sigma)
            detected = detector.detect(hotspots_df)
            candidates = detector.get_tasking_candidates(detected)
            run.detected_hotspots_count = len(candidates)

            # Store detected hotspots
            _store_detected_hotspots(detected, run)

            # Step 3: Simulate tasking
            tasking = TaskingSimulator()
            requests = tasking.create_tasking_requests(candidates, max_requests=15)
            _store_tasking_requests(requests, run)

            # Step 4: Generate plumes
            cm = CarbonMapperClient()
            hotspot_coords = [(h.latitude, h.longitude) for h in candidates]
            if use_demo:
                plumes = cm.generate_synthetic_plumes(hotspot_coords)
            else:
                from datetime import timedelta
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                plumes = cm.search_plumes(bbox=config.aoi_bbox, date_start=start_date, date_end=end_date)
                if not plumes:
                    plumes = cm.generate_synthetic_plumes(hotspot_coords)

            run.plumes_count = len(plumes)
            _store_plumes(plumes, run, is_synthetic=use_demo)

            # Step 5: Spatial join
            infra = InfrastructureDB(data_path=config.dataset_dir / "demo_industries.csv")
            joiner = SpatialJoiner(radius_km=config.spatial_join_radius_km)
            attributions = joiner.join(plumes, infra)
            run.attributions_count = len(attributions)
            _store_attributions(attributions, run)

            # Step 6: Plume inversion (top 5 emitters)
            inverter = PlumeInverter(stability_class="D")
            wind = WindField(use_live=not use_demo)
            top_emitters = sorted(attributions, key=lambda a: a.emission_rate_kg_hr, reverse=True)[:5]
            _run_and_store_inversions(top_emitters, inverter, wind, run)

            # Step 7: Reports (top 3 — LLM optional)
            if use_llm:
                try:
                    from src.agent.reporting_agent import ComplianceAuditAgent
                    agent = ComplianceAuditAgent(
                        model=config.ollama_model,
                        base_url=config.ollama_base_url,
                    )
                    top_for_report = sorted(attributions, key=lambda a: a.emission_rate_kg_hr, reverse=True)[:3]
                    reports = agent.generate_batch_reports(top_for_report)
                    run.reports_count = len(reports)
                    _store_reports(reports, run)
                except Exception as e:
                    run.error_message += f"LLM report generation failed: {str(e)}\n"

            run.status = 'completed'
            run.completed_at = timezone.now()
            run.save()

            return Response(
                PipelineRunSerializer(run).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            run.status = 'failed'
            run.error_message = traceback.format_exc()
            run.completed_at = timezone.now()
            run.save()
            return Response(
                {
                    'error': str(e),
                    'run_id': run.pk,
                    'status': 'failed',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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

        return Response({
            'total_facilities': total_facilities,
            'total_hotspots': total_hotspots,
            'total_detected': total_detected,
            'total_plumes': total_plumes,
            'total_attributions': total_attributions,
            'total_reports': total_reports,
            'total_pipeline_runs': total_runs,
            'critical_hotspots': critical_hotspots,
            'high_confidence_attributions': high_conf,
            'top_emitters': FacilityListSerializer(top_emitters, many=True).data,
            'recent_reports': AuditReportListSerializer(recent_reports, many=True).data,
            'facility_type_distribution': type_dist,
            'operator_distribution': operator_dist,
        })


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
            wind_speed_ms=p.wind_speed,
            wind_direction_deg=p.wind_direction,
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
    for report in reports:
        facility = Facility.objects.filter(facility_id=report.facility_id).first()
        if facility:
            AuditReport.objects.create(
                report_id=report.report_id,
                facility=facility,
                attribution=None,
                emission_rate_kg_hr=report.emission_rate_kg_hr,
                risk_level=report.risk_level.upper(),
                confidence=report.confidence,
                report_markdown=report.markdown,
                executive_summary=report.executive_summary,
                pipeline_run=run,
            )
