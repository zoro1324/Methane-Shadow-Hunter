"""
Django models for Methane Shadow Hunter API.

Maps to MySQL tables for:
- Facilities (oil & gas infrastructure)
- Methane hotspots (Sentinel-5P observations)
- Detected hotspots (anomaly-filtered)
- Plume observations (CarbonMapper)
- Attributed emissions (spatial join: plume → facility)
- Inversion results (Gaussian plume inversion)
- Tasking requests (high-res satellite tasking)
- Audit reports (compliance reports)
- Pipeline runs (execution tracking)
"""

from django.db import models


class Facility(models.Model):
    """Oil & gas infrastructure facility (from demo_industries.csv)."""

    FACILITY_TYPES = [
        ('refinery', 'Refinery'),
        ('pipeline', 'Pipeline'),
        ('compressor', 'Compressor'),
        ('terminal', 'Terminal'),
        ('well', 'Well'),
        ('gas_plant', 'Gas Plant'),
        ('tank_battery', 'Tank Battery'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('decommissioned', 'Decommissioned'),
    ]

    facility_id = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=FACILITY_TYPES)
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    operator = models.CharField(max_length=255)
    country = models.CharField(max_length=100, default='India')
    state = models.CharField(max_length=100, blank=True, default='Unknown')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'facilities'
        ordering = ['facility_id']
        verbose_name_plural = 'facilities'

    def __str__(self):
        return f"{self.facility_id} - {self.name}"


class MethaneHotspot(models.Model):
    """Raw Sentinel-5P TROPOMI CH4 observation point."""

    SEVERITY_CHOICES = [
        ('Severe', 'Severe'),
        ('Moderate', 'Moderate'),
        ('Low', 'Low'),
    ]

    system_index = models.CharField(max_length=64, unique=True, db_index=True)
    count = models.IntegerField(help_text='Observation count (proxy for CH4 column density)')
    label = models.IntegerField(default=1)
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'methane_hotspots'
        ordering = ['-count']

    def __str__(self):
        return f"{self.system_index} (count={self.count})"


class DetectedHotspot(models.Model):
    """Filtered hotspot that exceeds anomaly detection threshold."""

    PRIORITY_CHOICES = [
        (1, 'Critical'),
        (2, 'High'),
        (3, 'Moderate'),
    ]

    hotspot_id = models.CharField(max_length=32, unique=True, db_index=True)
    source_hotspot = models.ForeignKey(
        MethaneHotspot, on_delete=models.SET_NULL, null=True, blank=True, related_name='detections'
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    ch4_count = models.IntegerField()
    anomaly_score = models.FloatField()
    severity = models.CharField(max_length=16)
    requires_highres = models.BooleanField(default=False)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=3)
    pipeline_run = models.ForeignKey(
        'PipelineRun', on_delete=models.CASCADE, null=True, blank=True, related_name='detected_hotspots'
    )
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'detected_hotspots'
        ordering = ['priority', '-anomaly_score']

    def __str__(self):
        return f"{self.hotspot_id} (priority={self.priority}, score={self.anomaly_score})"


class PlumeObservation(models.Model):
    """CarbonMapper plume observation (real or synthetic)."""

    plume_id = models.CharField(max_length=64, unique=True, db_index=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    emission_rate_kg_hr = models.FloatField(help_text='Emission rate in kg/hr')
    wind_speed_ms = models.FloatField(help_text='Wind speed in m/s')
    wind_direction_deg = models.FloatField(help_text='Wind direction in degrees')
    plume_length_m = models.FloatField(null=True, blank=True)
    sector = models.CharField(max_length=64, blank=True)
    concentration_ppm = models.FloatField(null=True, blank=True)
    is_synthetic = models.BooleanField(default=True, help_text='True if generated, False if from API')
    pipeline_run = models.ForeignKey(
        'PipelineRun', on_delete=models.CASCADE, null=True, blank=True, related_name='plumes'
    )
    observed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'plume_observations'
        ordering = ['-emission_rate_kg_hr']

    def __str__(self):
        return f"{self.plume_id} ({self.emission_rate_kg_hr:.1f} kg/hr)"


class AttributedEmission(models.Model):
    """Spatial join result: plume attributed to nearest facility."""

    CONFIDENCE_CHOICES = [
        ('high', 'High (<500m)'),
        ('medium', 'Medium (<2km)'),
        ('low', 'Low (>2km)'),
    ]

    plume = models.ForeignKey(PlumeObservation, on_delete=models.CASCADE, related_name='attributions')
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='attributions')
    distance_km = models.FloatField(help_text='Distance between plume and facility in km')
    confidence = models.CharField(max_length=16, choices=CONFIDENCE_CHOICES)
    emission_rate_kg_hr = models.FloatField()
    pipeline_run = models.ForeignKey(
        'PipelineRun', on_delete=models.CASCADE, null=True, blank=True, related_name='attributions'
    )
    attributed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'attributed_emissions'
        ordering = ['-emission_rate_kg_hr']

    def __str__(self):
        return f"{self.plume.plume_id} → {self.facility.facility_id} ({self.distance_km:.2f}km)"


class InversionResult(models.Model):
    """Results from Gaussian plume inverse optimization."""

    attribution = models.OneToOneField(
        AttributedEmission, on_delete=models.CASCADE, related_name='inversion'
    )
    estimated_q_kg_hr = models.FloatField(help_text='Estimated emission rate (kg/hr)')
    estimated_q_kg_s = models.FloatField(help_text='Estimated emission rate (kg/s)')
    true_q_kg_hr = models.FloatField(null=True, blank=True)
    error_pct = models.FloatField(null=True, blank=True, help_text='Percentage error vs true')
    ci_lower_kg_hr = models.FloatField(help_text='95% CI lower bound')
    ci_upper_kg_hr = models.FloatField(help_text='95% CI upper bound')
    final_loss = models.FloatField()
    n_iterations = models.IntegerField()
    converged = models.BooleanField(default=False)
    pipeline_run = models.ForeignKey(
        'PipelineRun', on_delete=models.CASCADE, null=True, blank=True, related_name='inversions'
    )
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inversion_results'
        ordering = ['-estimated_q_kg_hr']

    def __str__(self):
        return f"Inversion: {self.estimated_q_kg_hr:.2f} kg/hr (err={self.error_pct:.1f}%)"


class TaskingRequest(models.Model):
    """High-resolution satellite tasking request."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('acquired', 'Acquired'),
        ('failed', 'Failed'),
    ]
    PRIORITY_CHOICES = [
        (1, 'Critical'),
        (2, 'High'),
        (3, 'Moderate'),
    ]

    request_id = models.CharField(max_length=64, unique=True, db_index=True)
    hotspot = models.ForeignKey(
        DetectedHotspot, on_delete=models.CASCADE, null=True, blank=True, related_name='tasking_requests'
    )
    satellite = models.CharField(max_length=64, default='CarbonMapper-Tanager')
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    pipeline_run = models.ForeignKey(
        'PipelineRun', on_delete=models.CASCADE, null=True, blank=True, related_name='tasking_requests'
    )
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tasking_requests'
        ordering = ['priority', '-requested_at']

    def __str__(self):
        return f"{self.request_id} ({self.satellite}, priority={self.priority})"


class AuditReport(models.Model):
    """Compliance audit report generated by the LLM agent."""

    RISK_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]

    report_id = models.CharField(max_length=64, unique=True, db_index=True)
    attribution = models.ForeignKey(
        AttributedEmission, on_delete=models.CASCADE, null=True, blank=True, related_name='reports'
    )
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='reports')
    emission_rate_kg_hr = models.FloatField()
    risk_level = models.CharField(max_length=16, choices=RISK_CHOICES)
    confidence = models.CharField(max_length=16)
    report_markdown = models.TextField(help_text='Full markdown report content')
    executive_summary = models.TextField(blank=True)
    pipeline_run = models.ForeignKey(
        'PipelineRun', on_delete=models.CASCADE, null=True, blank=True, related_name='reports'
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_reports'
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.report_id} - {self.facility.name} ({self.risk_level})"


class PipelineRun(models.Model):
    """Tracks a pipeline execution run."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    mode = models.CharField(max_length=16, default='demo', help_text='demo or live')
    use_llm = models.BooleanField(default=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    total_hotspots = models.IntegerField(default=0)
    detected_hotspots_count = models.IntegerField(default=0)
    plumes_count = models.IntegerField(default=0)
    attributions_count = models.IntegerField(default=0)
    reports_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'pipeline_runs'
        ordering = ['-started_at']

    def __str__(self):
        return f"Run #{self.pk} ({self.status}) - {self.started_at:%Y-%m-%d %H:%M}"
