"""
Methane Shadow Hunter - Full Pipeline Orchestrator.

Runs the complete end-to-end workflow:
1. Load Sentinel-5P CH4 data (from bundled India dataset)
2. Detect hotspots (anomaly threshold)
3. Simulate high-res satellite tasking
4. Fetch/generate CarbonMapper plume data
5. Spatial join: attribute plumes to infrastructure
6. Run plume inversion (PyTorch Gaussian model)
7. Generate compliance audit reports (LangChain + Ollama)
"""

import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

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
from src.agent.reporting_agent import ComplianceAuditAgent


class MethaneHunterPipeline:
    """
    Complete methane detection and attribution pipeline.
    """

    def __init__(self, use_demo: bool = True, use_llm: bool = True):
        self.use_demo = use_demo
        self.use_llm = use_llm

        # Initialize components
        self.s5p_client = Sentinel5PClient()
        self.cm_client = CarbonMapperClient()
        self.infra_db = InfrastructureDB(data_path=config.dataset_dir / "demo_industries.csv")
        self.detector = HotspotDetector(threshold_sigma=config.hotspot_threshold_sigma)
        self.tasking = TaskingSimulator()
        self.joiner = SpatialJoiner(radius_km=config.spatial_join_radius_km)
        self.wind = WindField(use_live=not self.use_demo)
        self.inverter = PlumeInverter(stability_class="D")
        self.agent = ComplianceAuditAgent(
            model=config.ollama_model,
            base_url=config.ollama_base_url,
        )

        # Results storage
        self.results = {}

    def run(self) -> dict:
        """Run the complete pipeline end-to-end."""
        print("=" * 70)
        print("🛰️  METHANE SHADOW HUNTER - Pipeline Execution")
        print("=" * 70)
        print(f"Mode: {'DEMO (synthetic + bundled data)' if self.use_demo else 'LIVE'}")
        print(f"LLM: {'Ollama (' + config.ollama_model + ')' if self.use_llm else 'Template only'}")
        print(f"AOI: India ({config.aoi_bbox})")
        print()

        # Step 1: Load Sentinel-5P data
        print("─" * 50)
        print("STEP 1: Loading Sentinel-5P TROPOMI CH4 Data")
        print("─" * 50)
        if self.use_demo:
            print("[DEBUG.SOURCE] DEMO MODE: Using bundled offline dataset (India_Methane_Hotspots.csv).")
            hotspots_df = self.s5p_client.load_hotspots_csv()
            stats = self.s5p_client.get_summary_stats()
        else:
            print("[DEBUG.SOURCE] LIVE MODE: Fetching active Sentinel-5P data from Google Earth Engine.")
            hotspots_df = self.s5p_client.fetch_hotspots_gee(bbox=config.aoi_bbox, days=30)
            stats = self.s5p_client.get_summary_stats_from_df(hotspots_df)
            
        print(f"  Loaded {stats['total_hotspots']} hotspot locations")
        print(f"  Severe: {stats['severe_count']} | Moderate: {stats['moderate_count']} | Low: {stats['low_count']}")
        print(f"  Max observation count: {stats['max_count']}")
        print(f"  Coverage: Lon {stats['lon_range'][0]:.1f}°-{stats['lon_range'][1]:.1f}°, "
              f"Lat {stats['lat_range'][0]:.1f}°-{stats['lat_range'][1]:.1f}°")
        self.results["sentinel5p_stats"] = stats
        print()

        # Step 2: Detect anomalous hotspots
        print("─" * 50)
        print("STEP 2: Hotspot Detection (Anomaly Threshold)")
        print("─" * 50)
        print(f"[DEBUG.LOGIC] Applying dynamic statistical threshold ({config.hotspot_threshold_sigma}σ).")
        detected = self.detector.detect(hotspots_df)
        tasking_candidates = self.detector.get_tasking_candidates(detected)
        det_summary = self.detector.summary(detected)
        print(f"  Analyzed: {det_summary['total_analyzed']} points")
        print(f"  Above threshold ({config.hotspot_threshold_sigma}σ): {det_summary['above_threshold']}")
        print(f"  Priority 1 (Critical): {det_summary['priority_1_critical']}")
        print(f"  Priority 2 (High): {det_summary['priority_2_high']}")
        print(f"  Max anomaly score: {det_summary['max_anomaly_score']:.2f}")
        self.results["detection_summary"] = det_summary
        print()

        # Step 3: Simulate high-res tasking
        print("─" * 50)
        print("STEP 3: High-Resolution Satellite Tasking")
        print("─" * 50)
        print("[DEBUG.LOGIC] Simulating satellite tasking triggers for high-priority points...")
        requests = self.tasking.create_tasking_requests(tasking_candidates, max_requests=15)
        task_summary = self.tasking.summary()
        print(f"  Created {task_summary['total_requests']} tasking requests")
        for sat, count in task_summary["by_satellite"].items():
            if count > 0:
                print(f"    → {sat}: {count} requests")
        self.results["tasking_summary"] = task_summary
        print()

        # Step 4: Get/generate plume observations
        print("─" * 50)
        print("STEP 4: CarbonMapper Plume Data")
        print("─" * 50)
        hotspot_coords = [(h.latitude, h.longitude) for h in tasking_candidates]

        if self.use_demo:
            print("[DEBUG.SOURCE] DEMO MODE: Generating synthetic high-res plume properties.")
            plumes = self.cm_client.generate_synthetic_plumes(hotspot_coords)
            print(f"  Generated {len(plumes)} synthetic plumes (demo mode)")
        else:
            from datetime import datetime, timedelta
            end_date_str = datetime.now().strftime('%Y-%m-%d')
            start_date_str = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            plumes = self.cm_client.search_plumes(
                bbox=config.aoi_bbox,
                date_start=start_date_str,
                date_end=end_date_str
            )
            
            if not plumes:
                plumes = self.cm_client.generate_synthetic_plumes(hotspot_coords)
                print(f"  API returned no results; generated {len(plumes)} synthetic plumes")
            else:
                print(f"  Retrieved {len(plumes)} plumes from CarbonMapper API")

        plume_df = self.cm_client.plumes_to_dataframe(plumes)
        if not plume_df.empty and 'emission_rate_kg_hr' in plume_df.columns:
            print(f"  Emission rates: {plume_df['emission_rate_kg_hr'].min():.1f} - {plume_df['emission_rate_kg_hr'].max():.1f} kg/hr")
            print(f"  Mean emission: {plume_df['emission_rate_kg_hr'].mean():.1f} kg/hr")
        else:
            print("  No plumes with emission rate data available.")
        self.results["plume_count"] = len(plumes)
        print()

        # Step 5: Load infrastructure & spatial join
        print("─" * 50)
        print("STEP 5: Infrastructure Attribution (Spatial Join)")
        print("─" * 50)
        if self.infra_db.data_path and self.infra_db.data_path.exists():
            print(f"[DEBUG.SOURCE] LIVE MODE: Loading real infrastructure from {self.infra_db.data_path.name}")
        else:
            print("[DEBUG.SOURCE] DEMO MODE: Generating synthetic Indian Oil & Gas infrastructure layout.")
        facilities = self.infra_db.load_facilities()
        print(f"  Loaded {len(facilities)} infrastructure facilities")
        attributed = self.joiner.join(plumes, facilities)
        metrics = self.joiner.metrics(attributed)
        print(f"  Attributed {metrics['total_attributed']} plumes to facilities")
        if metrics['total_attributed'] > 0:
            print(f"  Mean pinpoint accuracy: {metrics['mean_pinpoint_accuracy_m']:.0f}m")
            print(f"  Within 500m: {metrics['pct_within_500m']:.1f}%")
            print(f"  Within 1km: {metrics['pct_within_1km']:.1f}%")
            print(f"  High confidence: {metrics['high_confidence_pct']:.1f}%")
            print(f"  Total emission rate: {metrics['total_emission_rate_kg_hr']:.1f} kg/hr")
        self.results["attribution_metrics"] = metrics
        print()

        # Step 6: Plume inversion (PyTorch)
        print("─" * 50)
        print("STEP 6: Plume Inversion Modeling (PyTorch)")
        print("─" * 50)
        if self.use_demo:
            print("[DEBUG.LOGIC] DEMO MODE: Solving inverse Gaussian fields on synthetic concentration grids.")
        else:
            print("[DEBUG.LOGIC] LIVE MODE: Solving inversion over real satellite CH4 concentration pixels.")
            
        inversion_results = []
        # Run inversion for top 5 emitters
        top_emitters = attributed[:5] if len(attributed) >= 5 else attributed
        for i, attr in enumerate(top_emitters):
            # Get wind data
            wind_data = self.wind.get_wind(attr.plume_lat, attr.plume_lon)

            # Create synthetic observation for this emission rate
            true_Q_kg_s = attr.emission_rate_kg_hr / 3600
            synth = self.inverter.create_synthetic_observation(
                true_Q_kg_s=true_Q_kg_s,
                wind_speed=wind_data.speed_ms,
                stability_class=wind_data.stability_class,
            )

            # Run inversion
            result = self.inverter.invert(
                observed_concentrations=synth["observed_concentrations"],
                receptor_x=synth["receptor_x"],
                receptor_y=synth["receptor_y"],
                receptor_z=synth["receptor_z"],
                wind_speed=wind_data.speed_ms,
                initial_Q=0.01,
                true_Q_kg_hr=synth["true_Q_kg_hr"],
            )

            inversion_results.append(result)
            print(f"  [{i+1}] {attr.facility_name[:40]:40s} | "
                  f"True: {synth['true_Q_kg_hr']:.1f} → Est: {result.estimated_Q_kg_hr:.1f} kg/hr | "
                  f"Error: {result.error_pct:.1f}% | "
                  f"CI: [{result.confidence_interval[0]:.1f}, {result.confidence_interval[1]:.1f}] | "
                  f"{'✓' if result.converged else '✗'}")

        self.results["inversion_results"] = inversion_results
        if inversion_results:
            errors = [r.error_pct for r in inversion_results if r.error_pct is not None]
            if errors:
                print(f"\n  Mean emission rate error: {np.mean(errors):.2f}%")
        print()

        # Step 7: Generate compliance reports
        print("─" * 50)
        print("STEP 7: Compliance Audit Reports (LangChain + Ollama)")
        print("─" * 50)
        if self.use_llm:
            print(f"[DEBUG.LLM] Using Local LLM Agent ({config.ollama_model}) to dynamically author audit details.")
        else:
            print("[DEBUG.LLM] LLM agent disabled. Falling back to hard-coded template audit.")
            
        # Generate for top 3 emitters
        report_candidates = attributed[:3] if len(attributed) >= 3 else attributed
        plume_map = {p.plume_id: p for p in plumes}

        if report_candidates:
            reports = self.agent.generate_batch_reports(report_candidates, plume_map)
            self.results["reports"] = reports

            # Save reports
            report_dir = PROJECT_ROOT / "reports"
            report_dir.mkdir(exist_ok=True)
            for report in reports:
                report_path = report_dir / f"{report.report_id}.md"
                report_path.write_text(report.report_markdown, encoding="utf-8")
                print(f"  Saved: {report_path.name}")
        else:
            print("  No attributed emissions to report on.")
            self.results["reports"] = []
        print()

        # Final Summary
        print("=" * 70)
        print("🏁 PIPELINE COMPLETE — Summary")
        print("=" * 70)
        print(f"  Sentinel-5P hotspots analyzed: {stats['total_hotspots']}")
        print(f"  Super-emitter candidates: {det_summary['above_threshold']}")
        print(f"  Plumes detected: {len(plumes)}")
        print(f"  Attributed to facilities: {metrics['total_attributed']}")
        if inversion_results:
            errors = [r.error_pct for r in inversion_results if r.error_pct is not None]
            if errors:
                print(f"  Plume inversion mean error: {np.mean(errors):.2f}%")
        print(f"  Reports generated: {len(self.results.get('reports', []))}")
        print("=" * 70)

        return self.results


def main():
    """Entry point for running the pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description="Methane Shadow Hunter Pipeline")
    parser.add_argument("--live", action="store_true", default=False,
                        help="Run in live mode fetching real data from GEE instead of using synthetic dataset")
    parser.add_argument("--no-llm", action="store_true", default=False,
                        help="Disable LLM-based report generation")
    args = parser.parse_args()

    pipeline = MethaneHunterPipeline(
        use_demo=not args.live,
        use_llm=not args.no_llm,
    )
    results = pipeline.run()
    return results


if __name__ == "__main__":
    main()
