"""
Django REST Framework serializers for Methane Shadow Hunter API.
"""

from rest_framework import serializers
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


# ─── Facility ───────────────────────────────────────────────────────────────

class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = '__all__'


class FacilityListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""
    class Meta:
        model = Facility
        fields = [
            'id', 'facility_id', 'name', 'type', 'latitude', 'longitude',
            'operator', 'state', 'status',
        ]


# ─── Methane Hotspot ────────────────────────────────────────────────────────

class MethaneHotspotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MethaneHotspot
        fields = '__all__'


# ─── Detected Hotspot ───────────────────────────────────────────────────────

class DetectedHotspotSerializer(serializers.ModelSerializer):
    priority_label = serializers.SerializerMethodField()

    class Meta:
        model = DetectedHotspot
        fields = '__all__'

    def get_priority_label(self, obj):
        labels = {1: 'Critical', 2: 'High', 3: 'Moderate'}
        return labels.get(obj.priority, 'Unknown')


# ─── Plume Observation ──────────────────────────────────────────────────────

class PlumeObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlumeObservation
        fields = '__all__'


# ─── Attributed Emission ────────────────────────────────────────────────────

class AttributedEmissionSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    facility_type = serializers.CharField(source='facility.type', read_only=True)
    facility_operator = serializers.CharField(source='facility.operator', read_only=True)
    plume_id = serializers.CharField(source='plume.plume_id', read_only=True)

    class Meta:
        model = AttributedEmission
        fields = '__all__'


class AttributedEmissionDetailSerializer(serializers.ModelSerializer):
    facility = FacilitySerializer(read_only=True)
    plume = PlumeObservationSerializer(read_only=True)
    inversion = serializers.SerializerMethodField()

    class Meta:
        model = AttributedEmission
        fields = '__all__'

    def get_inversion(self, obj):
        try:
            return InversionResultSerializer(obj.inversion).data
        except InversionResult.DoesNotExist:
            return None


# ─── Inversion Result ───────────────────────────────────────────────────────

class InversionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = InversionResult
        fields = '__all__'


# ─── Tasking Request ────────────────────────────────────────────────────────

class TaskingRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskingRequest
        fields = '__all__'


# ─── Audit Report ───────────────────────────────────────────────────────────

class AuditReportSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source='facility.name', read_only=True)

    class Meta:
        model = AuditReport
        fields = '__all__'


class AuditReportListSerializer(serializers.ModelSerializer):
    """Lighter serializer without full markdown content."""
    facility_name = serializers.CharField(source='facility.name', read_only=True)

    class Meta:
        model = AuditReport
        fields = [
            'id', 'report_id', 'facility', 'facility_name',
            'emission_rate_kg_hr', 'risk_level', 'confidence',
            'executive_summary', 'generated_at',
        ]


# ─── Pipeline Run ──────────────────────────────────────────────────────────

class PipelineRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineRun
        fields = '__all__'


class PipelineRunDetailSerializer(serializers.ModelSerializer):
    detected_hotspots = DetectedHotspotSerializer(many=True, read_only=True)
    plumes = PlumeObservationSerializer(many=True, read_only=True)
    attributions = AttributedEmissionSerializer(many=True, read_only=True)
    reports = AuditReportListSerializer(many=True, read_only=True)

    class Meta:
        model = PipelineRun
        fields = '__all__'


# ─── Dashboard / Summary ───────────────────────────────────────────────────

class DashboardSummarySerializer(serializers.Serializer):
    """Non-model serializer for dashboard summary endpoint."""
    total_facilities = serializers.IntegerField()
    total_hotspots = serializers.IntegerField()
    total_detected = serializers.IntegerField()
    total_plumes = serializers.IntegerField()
    total_attributions = serializers.IntegerField()
    total_reports = serializers.IntegerField()
    total_pipeline_runs = serializers.IntegerField()
    critical_hotspots = serializers.IntegerField()
    high_confidence_attributions = serializers.IntegerField()
    top_emitters = FacilityListSerializer(many=True)
    recent_reports = AuditReportListSerializer(many=True)
    facility_type_distribution = serializers.DictField()
    operator_distribution = serializers.DictField()


class PipelineTriggerSerializer(serializers.Serializer):
    """Serializer for triggering a pipeline run."""
    mode = serializers.ChoiceField(choices=['demo', 'live'], default='demo')
    use_llm = serializers.BooleanField(default=False)
