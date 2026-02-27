from django.contrib import admin
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


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['facility_id', 'name', 'type', 'operator', 'state', 'status']
    list_filter = ['type', 'operator', 'status']
    search_fields = ['facility_id', 'name', 'operator']


@admin.register(MethaneHotspot)
class MethaneHotspotAdmin(admin.ModelAdmin):
    list_display = ['system_index', 'count', 'severity', 'latitude', 'longitude']
    list_filter = ['severity']


@admin.register(DetectedHotspot)
class DetectedHotspotAdmin(admin.ModelAdmin):
    list_display = ['hotspot_id', 'priority', 'anomaly_score', 'severity', 'requires_highres']
    list_filter = ['priority', 'severity', 'requires_highres']


@admin.register(PlumeObservation)
class PlumeObservationAdmin(admin.ModelAdmin):
    list_display = ['plume_id', 'emission_rate_kg_hr', 'wind_speed_ms', 'sector', 'is_synthetic']
    list_filter = ['sector', 'is_synthetic']


@admin.register(AttributedEmission)
class AttributedEmissionAdmin(admin.ModelAdmin):
    list_display = ['plume', 'facility', 'distance_km', 'confidence', 'emission_rate_kg_hr']
    list_filter = ['confidence']


@admin.register(InversionResult)
class InversionResultAdmin(admin.ModelAdmin):
    list_display = ['attribution', 'estimated_q_kg_hr', 'error_pct', 'converged']
    list_filter = ['converged']


@admin.register(TaskingRequest)
class TaskingRequestAdmin(admin.ModelAdmin):
    list_display = ['request_id', 'satellite', 'priority', 'status']
    list_filter = ['satellite', 'priority', 'status']


@admin.register(AuditReport)
class AuditReportAdmin(admin.ModelAdmin):
    list_display = ['report_id', 'facility', 'emission_rate_kg_hr', 'risk_level', 'confidence']
    list_filter = ['risk_level', 'confidence']
    search_fields = ['report_id', 'facility__name']


@admin.register(PipelineRun)
class PipelineRunAdmin(admin.ModelAdmin):
    list_display = ['id', 'mode', 'status', 'total_hotspots', 'attributions_count', 'reports_count', 'started_at']
    list_filter = ['status', 'mode']
