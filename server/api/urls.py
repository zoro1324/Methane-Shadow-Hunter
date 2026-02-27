"""
API URL routing for Methane Shadow Hunter.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'facilities', views.FacilityViewSet, basename='facility')
router.register(r'hotspots', views.MethaneHotspotViewSet, basename='hotspot')
router.register(r'detected-hotspots', views.DetectedHotspotViewSet, basename='detected-hotspot')
router.register(r'plumes', views.PlumeObservationViewSet, basename='plume')
router.register(r'attributions', views.AttributedEmissionViewSet, basename='attribution')
router.register(r'inversions', views.InversionResultViewSet, basename='inversion')
router.register(r'tasking-requests', views.TaskingRequestViewSet, basename='tasking-request')
router.register(r'reports', views.AuditReportViewSet, basename='report')
router.register(r'pipeline-runs', views.PipelineRunViewSet, basename='pipeline-run')

urlpatterns = [
    # ViewSet routes (CRUD + custom actions)
    path('', include(router.urls)),

    # Pipeline trigger
    path('pipeline/trigger/', views.PipelineTriggerView.as_view(), name='pipeline-trigger'),

    # Dashboard
    path('dashboard/summary/', views.DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('dashboard/trend/', views.DashboardTrendView.as_view(), name='dashboard-trend'),

    # GeoJSON export endpoints (for map rendering)
    path('geojson/facilities/', views.facilities_geojson, name='geojson-facilities'),
    path('geojson/hotspots/', views.hotspots_geojson, name='geojson-hotspots'),
    path('geojson/attributions/', views.attributions_geojson, name='geojson-attributions'),

    # Google Earth Engine endpoints (heatmap)
    path('gee/ch4-tiles/', views.gee_ch4_tiles, name='gee-ch4-tiles'),
    path('gee/ch4-heatmap/', views.gee_ch4_heatmap, name='gee-ch4-heatmap'),
]
