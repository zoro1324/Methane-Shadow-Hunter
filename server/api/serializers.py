"""
Django REST Framework serializers for Methane Shadow Hunter API.
"""

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
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
    severity_distribution = serializers.DictField()
    total_tasking_requests = serializers.IntegerField()
    last_pipeline_run = serializers.DictField(allow_null=True)


class PipelineTriggerSerializer(serializers.Serializer):
    """Serializer for triggering a pipeline run."""
    mode = serializers.ChoiceField(choices=['demo', 'live'], default='demo')
    use_llm = serializers.BooleanField(default=False)


# ─── Authentication ─────────────────────────────────────────────────────────

class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration."""
    username = serializers.CharField(max_length=150, min_length=3)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, default='')
    last_name = serializers.CharField(max_length=150, required=False, default='')

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        # Run Django password validators
        validate_password(data['password'])
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
