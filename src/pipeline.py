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
import time
import numpy as np
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ─── ANSI colour helpers ──────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    BLUE    = "\033[94m"
    WHITE   = "\033[97m"

def _col(text: str, colour: str) -> str:
    return f"{colour}{text}{C.RESET}"

def _ok(text: str)   -> str: return _col(f"  ✔  {text}", C.GREEN)
def _info(text: str) -> str: return _col(f"  ·  {text}", C.CYAN)
def _warn(text: str) -> str: return _col(f"  ⚠  {text}", C.YELLOW)
def _data(text: str) -> str: return f"     {C.DIM}{text}{C.RESET}"

_STEP_TITLES = {
    1: ("🌍", "Fast Global Sweep",        "Sentinel-5P TROPOMI — Last-30-day CH4 mosaic over India"),
    2: ("🔍", "Anomaly Detection",         "Statistical σ-threshold filter to isolate genuine super-emitters"),
    3: ("📡", "High-Res Tasking Trigger",  "Simulating CarbonMapper Tanager / GHGSat tasking requests"),
    4: ("🛰️ ", "High-Res Plume Imaging",   "CarbonMapper STAC API — precise plume geometry & emission estimates"),
    5: ("🏭", "Infrastructure Attribution","Haversine spatial join → Who is responsible for each leak?"),
    6: ("⚛️ ", "Plume Inversion (PyTorch)","Gaussian dispersion inversion with live Open-Meteo wind data"),
    7: ("📋", "Autonomous Audit Reports",  "LangChain + Ollama compliance officer generates regulatory filings"),
}

def _step_banner(n: int) -> float:
    """Print a visually distinct step header and return the start timestamp."""
    icon, short, desc = _STEP_TITLES[n]
    width = 70
    bar   = "═" * width
    print()
    print(_col(bar, C.BLUE))
    print(_col(f"  STEP {n}/7  {icon}  {short}", C.BOLD + C.WHITE))
    print(_col(f"  {desc}", C.DIM + C.CYAN))
    print(_col(bar, C.BLUE))
    return time.time()

def _step_done(t0: float, label: str = ""):
    elapsed = time.time() - t0
    tag = f" — {label}" if label else ""
    print(_col(f"\n  ✔  Step complete{tag}  [{elapsed:.2f}s]", C.GREEN))

def _table_row(cols: list, widths: list) -> str:
    return "  " + "  ".join(str(c).ljust(w) for c, w in zip(cols, widths))

def _divider(char="─", width=66):
    print(f"  {C.DIM}{char * width}{C.RESET}")

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
        """Run the complete pipeline end-to-end with rich debug output."""
        pipeline_start = time.time()

        # ── Master header ────────────────────────────────────────────────────
        width = 70
        print()
        print(_col("█" * width, C.CYAN))
        print(_col("█" + " " * (width - 2) + "█", C.CYAN))
        title = "🛰️   METHANE SHADOW HUNTER  —  PIPELINE EXECUTION"
        pad   = (width - 2 - len(title)) // 2
        print(_col("█" + " " * pad + title + " " * (width - 2 - pad - len(title)) + "█", C.CYAN + C.BOLD))
        print(_col("█" + " " * (width - 2) + "█", C.CYAN))
        print(_col("█" * width, C.CYAN))
        print()
        mode_str  = _col("OFFLINE (bundled dataset)", C.YELLOW) if self.use_demo else _col("LIVE (GEE + APIs)", C.GREEN)
        llm_str   = _col(f"Ollama / {config.ollama_model}", C.GREEN) if self.use_llm else _col("Disabled", C.YELLOW)
        print(f"  {C.BOLD}Mode   :{C.RESET} {mode_str}")
        print(f"  {C.BOLD}LLM    :{C.RESET} {llm_str}")
        print(f"  {C.BOLD}AOI    :{C.RESET} India  "
              f"Lon {config.aoi_min_lon}°–{config.aoi_max_lon}°  "
              f"Lat {config.aoi_min_lat}°–{config.aoi_max_lat}°")
        print(f"  {C.BOLD}Started:{C.RESET} {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")

        # ════════════════════════════════════════════════════════════════════
        # STEP 1 — Sentinel-5P
        # ════════════════════════════════════════════════════════════════════
        t0 = _step_banner(1)

        if self.use_demo:
            print(_info("Source  : models/dataset/India_Methane_Hotspots.csv"))
            print(_info("Loading bundled 30-day TROPOMI CH4 mosaic …"))
            hotspots_df = self.s5p_client.load_hotspots_csv()
            stats = self.s5p_client.get_summary_stats()
            print(_info(f"Dataset : {len(hotspots_df)} rows × {len(hotspots_df.columns)} columns"))
        else:
            print(_info("Source  : Google Earth Engine  COPERNICUS/S5P/OFFL/L3_CH4"))
            print(_info("Querying GEE for last 30 days over AOI …"))
            hotspots_df = self.s5p_client.fetch_hotspots_gee(bbox=config.aoi_bbox, days=30)
            stats = self.s5p_client.get_summary_stats_from_df(hotspots_df)

        _divider()
        print(_ok(f"Loaded  {stats['total_hotspots']} hotspot locations"))
        _divider()
        sev_bar = (f"{C.RED}Severe {stats['severe_count']:>3}{C.RESET}  │  "
                   f"{C.YELLOW}Moderate {stats['moderate_count']:>3}{C.RESET}  │  "
                   f"{C.DIM}Low {stats['low_count']:>3}{C.RESET}")
        print(f"     Severity  :  {sev_bar}")
        print(_data(f"Max CH4 count  : {stats['max_count']}"))
        print(_data(f"Lon coverage   : {stats['lon_range'][0]:.2f}° → {stats['lon_range'][1]:.2f}°"))
        print(_data(f"Lat coverage   : {stats['lat_range'][0]:.2f}° → {stats['lat_range'][1]:.2f}°"))

        # Sample rows
        if not hotspots_df.empty:
            _divider("·")
            print(_data("Sample rows (top 3 by CH4 count):"))
            sample = hotspots_df.nlargest(3, "count") if "count" in hotspots_df.columns else hotspots_df.head(3)
            hdrs = ["latitude", "longitude", "count", "severity"]
            hdrs = [c for c in hdrs if c in sample.columns]
            widths = [12, 12, 10, 12][:len(hdrs)]
            print(_data("  ".join(h.ljust(w) for h, w in zip(hdrs, widths))))
            for _, row in sample.iterrows():
                vals = [f"{row[h]:.4f}" if isinstance(row[h], float) else str(row[h]) for h in hdrs]
                print(_data("  ".join(v.ljust(w) for v, w in zip(vals, widths))))

        self.results["sentinel5p_stats"] = stats
        _step_done(t0, f"{stats['total_hotspots']} hotspots loaded")

        # ════════════════════════════════════════════════════════════════════
        # STEP 2 — Anomaly Detection
        # ════════════════════════════════════════════════════════════════════
        t0 = _step_banner(2)

        sigma = config.hotspot_threshold_sigma
        print(_info(f"Algorithm : Z-score threshold  σ = {sigma}"))
        print(_info(f"Strategy  : Flag pixels > (mean + {sigma}×std) of CH4 count"))
        print(_info("Running detection …"))

        detected           = self.detector.detect(hotspots_df)
        tasking_candidates = self.detector.get_tasking_candidates(detected)
        det_summary        = self.detector.summary(detected)

        _divider()
        print(_ok(f"Threshold passed  : {det_summary['above_threshold']} / {det_summary['total_analyzed']} points"))
        _divider()
        print(_data(f"Priority 1 — CRITICAL  : {det_summary['priority_1_critical']}"))
        print(_data(f"Priority 2 — HIGH      : {det_summary['priority_2_high']}"))
        print(_data(f"Max anomaly score      : {det_summary['max_anomaly_score']:.4f} σ"))
        print(_data(f"Tasking candidates     : {len(tasking_candidates)}"))

        if tasking_candidates:
            _divider("·")
            print(_data("Top 5 tasking candidates (sorted by anomaly score):"))
            print(_data(f"  {'#':<4} {'Lat':>10} {'Lon':>11} {'Score':>8} {'Severity':<12} {'Priority'}"))
            print(_data(f"  {'─'*4} {'─'*10} {'─'*11} {'─'*8} {'─'*12} {'─'*8}"))
            for i, h in enumerate(tasking_candidates[:5], 1):
                sev_col = C.RED if h.severity == "Severe" else (C.YELLOW if h.severity == "Moderate" else C.DIM)
                print(_data(f"  {i:<4} {h.latitude:>10.4f} {h.longitude:>11.4f} "
                             f"{h.anomaly_score:>8.4f} "
                             f"{sev_col}{h.severity:<12}{C.RESET} P{h.ch4_count}"))

        self.results["detection_summary"] = det_summary
        _step_done(t0, f"{det_summary['above_threshold']} super-emitter candidates identified")

        # ════════════════════════════════════════════════════════════════════
        # STEP 3 — High-Res Tasking
        # ════════════════════════════════════════════════════════════════════
        t0 = _step_banner(3)

        print(_info("Evaluating each anomaly candidate against tasking criteria …"))
        print(_info("Satellites available: CarbonMapper-Tanager, GHGSat, PRISMA"))
        requests_list = self.tasking.create_tasking_requests(tasking_candidates, max_requests=15)
        task_summary  = self.tasking.summary()

        _divider()
        print(_ok(f"Tasking requests created  : {task_summary['total_requests']}"))
        _divider()
        for sat, count in task_summary["by_satellite"].items():
            if count > 0:
                bar = "█" * count
                print(_data(f"  {sat:<30}  {C.CYAN}{bar}{C.RESET}  {count}"))

        if requests_list:
            _divider("·")
            print(_data("First 3 tasking requests:"))
            for r in requests_list[:3]:
                coords = f"({r.latitude:.4f}, {r.longitude:.4f})" if hasattr(r, "latitude") else ""
                sat    = getattr(r, "satellite", "—")
                pri    = getattr(r, "priority",  "—")
                print(_data(f"  Satellite: {sat:<28} Priority: {pri}  {coords}"))

        self.results["tasking_summary"] = task_summary
        _step_done(t0, f"{task_summary['total_requests']} satellite acquisitions queued")

        # ════════════════════════════════════════════════════════════════════
        # STEP 4 — CarbonMapper Plume Data
        # ════════════════════════════════════════════════════════════════════
        t0 = _step_banner(4)

        hotspot_coords = [(h.latitude, h.longitude) for h in tasking_candidates]

        if self.use_demo:
            print(_info("Source   : Synthetic high-res plumes (offline mode)"))
            print(_info("Model    : Log-normal emission distribution  (μ=3.9, σ=1.0)"))
            print(_info("Jitter   : ±0.005° spatial noise on hotspot centroids"))
            print(_info("Generating plumes …"))
            plumes = self.cm_client.generate_synthetic_plumes(hotspot_coords)
            print(_ok(f"Generated {len(plumes)} modelled plumes"))
        else:
            from datetime import datetime as _dt, timedelta
            end_date_str   = _dt.now().strftime('%Y-%m-%d')
            start_date_str = (_dt.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            print(_info(f"Querying CarbonMapper STAC  {start_date_str} → {end_date_str}"))
            plumes = self.cm_client.search_plumes(
                bbox=config.aoi_bbox, date_start=start_date_str, date_end=end_date_str)
            if not plumes:
                print(_warn("STAC returned 0 results (tasking lag). Falling back to synthetic."))
                plumes = self.cm_client.generate_synthetic_plumes(hotspot_coords)
                print(_ok(f"Generated {len(plumes)} modelled plumes (fallback)"))
            else:
                print(_ok(f"Retrieved {len(plumes)} plumes from CarbonMapper STAC API"))

        plume_df = self.cm_client.plumes_to_dataframe(plumes)
        if not plume_df.empty and "emission_rate_kg_hr" in plume_df.columns:
            _divider()
            rates = plume_df["emission_rate_kg_hr"]
            print(_data(f"Emission range  : {rates.min():.1f} – {rates.max():.1f} kg/hr"))
            print(_data(f"Mean emission   : {rates.mean():.1f} kg/hr"))
            print(_data(f"Median emission : {rates.median():.1f} kg/hr"))
            print(_data(f"Std deviation   : {rates.std():.1f} kg/hr"))
            _divider("·")
            print(_data("Top 5 plumes by emission rate:"))
            print(_data(f"  {'ID':<12} {'Lat':>9} {'Lon':>10} {'kg/hr':>8} {'Length(m)':>10} {'Quality':<8} {'Source'}"))
            print(_data(f"  {'─'*12} {'─'*9} {'─'*10} {'─'*8} {'─'*10} {'─'*8} {'─'*10}"))
            for _, row in plume_df.nlargest(5, "emission_rate_kg_hr").iterrows():
                q_col = C.RED if row["emission_rate_kg_hr"] > 200 else (C.YELLOW if row["emission_rate_kg_hr"] > 80 else C.DIM)
                print(_data(
                    f"  {str(row['plume_id']):<12} "
                    f"{row['latitude']:>9.4f} {row['longitude']:>10.4f} "
                    f"{q_col}{row['emission_rate_kg_hr']:>8.1f}{C.RESET} "
                    f"{row['plume_length_m']:>10.0f} "
                    f"{row['quality_flag']:<8} {row['source']}"))

        self.results["plume_count"] = len(plumes)
        _step_done(t0, f"{len(plumes)} plumes characterised")

        # ════════════════════════════════════════════════════════════════════
        # STEP 5 — Infrastructure Attribution
        # ════════════════════════════════════════════════════════════════════
        t0 = _step_banner(5)

        src = self.infra_db.data_path.name if (self.infra_db.data_path and self.infra_db.data_path.exists()) else "built-in registry"
        print(_info(f"Infrastructure source : {src}"))
        print(_info(f"Join algorithm        : Haversine distance ≤ {self.joiner.radius_km} km"))
        print(_info("Loading facilities and computing nearest-neighbour distances …"))

        facilities = self.infra_db.load_facilities()
        print(_ok(f"Loaded {len(facilities)} infrastructure facilities"))

        fac_types = {}
        for f in facilities:
            fac_types[f.facility_type] = fac_types.get(f.facility_type, 0) + 1
        _divider("·")
        print(_data("Facility type breakdown:"))
        for ftype, cnt in sorted(fac_types.items(), key=lambda x: -x[1]):
            bar = "▪" * min(cnt, 20)
            print(_data(f"  {ftype:<16}  {C.CYAN}{bar}{C.RESET}  {cnt}"))

        print(_info("Joining plumes to nearest facility within radius …"))
        attributed = self.joiner.join(plumes, facilities)
        metrics    = self.joiner.metrics(attributed)

        _divider()
        if metrics["total_attributed"] > 0:
            print(_ok(f"Attributed  {metrics['total_attributed']} / {len(plumes)} plumes  →  facilities"))
            _divider()
            print(_data(f"Mean pinpoint accuracy  : {metrics['mean_pinpoint_accuracy_m']:.0f} m"))
            print(_data(f"≤ 500 m accuracy        : {metrics['pct_within_500m']:.1f}%"))
            print(_data(f"≤ 1 km accuracy         : {metrics['pct_within_1km']:.1f}%"))
            print(_data(f"High confidence joins   : {metrics['high_confidence_pct']:.1f}%"))
            print(_data(f"Total attributed load   : {metrics['total_emission_rate_kg_hr']:.1f} kg/hr"))
            _divider("·")
            print(_data("Attribution table (all results):"))
            print(_data(f"  {'Facility':<40} {'Operator':<22} {'Dist(m)':>8} {'kg/hr':>8} {'Conf'}"))
            print(_data(f"  {'─'*40} {'─'*22} {'─'*8} {'─'*8} {'─'*6}"))
            for a in attributed:
                conf_col = C.GREEN if a.confidence == "high" else (C.YELLOW if a.confidence == "medium" else C.DIM)
                rate_col = C.RED   if a.emission_rate_kg_hr > 150 else (C.YELLOW if a.emission_rate_kg_hr > 60 else C.RESET)
                print(_data(
                    f"  {a.facility_name[:40]:<40} "
                    f"{a.operator[:22]:<22} "
                    f"{a.pinpoint_accuracy_m:>8.0f} "
                    f"{rate_col}{a.emission_rate_kg_hr:>8.1f}{C.RESET} "
                    f"{conf_col}{a.confidence}{C.RESET}"))
        else:
            print(_warn(f"0 plumes attributed (no facility within {self.joiner.radius_km} km of any plume)"))

        self.results["attribution_metrics"] = metrics
        _step_done(t0, f"{metrics['total_attributed']} facility attributions")

        # ════════════════════════════════════════════════════════════════════
        # STEP 6 — Plume Inversion (PyTorch)
        # ════════════════════════════════════════════════════════════════════
        t0 = _step_banner(6)

        wind_src = "Open-Meteo live wind API" if not self.use_demo else "synthetic wind field (offline)"
        print(_info(f"Physics model  : Gaussian plume dispersion (Pasquill–Gifford class D)"))
        print(_info(f"Wind data      : {wind_src}"))
        print(_info(f"Optimisation   : PyTorch gradient-based emission rate inversion"))
        print(_info("Running inversion for top 5 attributed emitters …"))
        _divider()

        inversion_results = []
        top_emitters = attributed[:5] if len(attributed) >= 5 else attributed

        for i, attr in enumerate(top_emitters, 1):
            wind_data  = self.wind.get_wind(attr.plume_lat, attr.plume_lon)
            true_Q_kg_s = attr.emission_rate_kg_hr / 3600
            synth = self.inverter.create_synthetic_observation(
                true_Q_kg_s=true_Q_kg_s,
                wind_speed=wind_data.speed_ms,
                stability_class=wind_data.stability_class,
            )
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

            conv_icon = _col("✔ converged", C.GREEN) if result.converged else _col("✗ not converged", C.RED)
            err_col   = C.GREEN if result.error_pct < 15 else (C.YELLOW if result.error_pct < 30 else C.RED)
            print(f"  {C.BOLD}[{i}]{C.RESET} {attr.facility_name[:38]:<38}")
            print(_data(f"  True rate  : {synth['true_Q_kg_hr']:>8.2f} kg/hr"))
            print(_data(f"  Estimated  : {result.estimated_Q_kg_hr:>8.2f} kg/hr"
                         f"   95% CI [{result.confidence_interval[0]:.1f}, {result.confidence_interval[1]:.1f}]"))
            print(_data(f"  Error      : {err_col}{result.error_pct:.2f}%{C.RESET}"
                         f"   Wind: {wind_data.speed_ms:.1f} m/s  Dir: {wind_data.direction_deg:.0f}°"
                         f"   Status: {conv_icon}"))
            if i < len(top_emitters):
                _divider("·")

        if inversion_results:
            errors = [r.error_pct for r in inversion_results if r.error_pct is not None]
            if errors:
                _divider()
                mean_err = np.mean(errors)
                err_col  = C.GREEN if mean_err < 15 else (C.YELLOW if mean_err < 30 else C.RED)
                print(_ok(f"Mean inversion error : {err_col}{mean_err:.2f}%{C.RESET}"))

        self.results["inversion_results"] = inversion_results
        _step_done(t0, f"{len(inversion_results)} emission rates solved")

        # ════════════════════════════════════════════════════════════════════
        # STEP 7 — Compliance Audit Reports
        # ════════════════════════════════════════════════════════════════════
        t0 = _step_banner(7)

        if self.use_llm:
            print(_info(f"Agent model    : {config.ollama_model}  @  {config.ollama_base_url}"))
            print(_info("Agent role     : Regulatory compliance officer"))
            print(_info("Output format  : Markdown audit report (exec summary + risk + remediation)"))
            print(_info("Generating reports for top 3 attributed emitters …"))
        else:
            print(_warn("LLM disabled — using template-based fallback reporter"))

        report_candidates = attributed[:3] if len(attributed) >= 3 else attributed
        plume_map         = {p.plume_id: p for p in plumes}

        if report_candidates:
            reports = self.agent.generate_batch_reports(report_candidates, plume_map)
            self.results["reports"] = reports

            report_dir = PROJECT_ROOT / "reports"
            report_dir.mkdir(exist_ok=True)

            _divider()
            for report in reports:
                risk_col = (C.RED    if "CRITICAL" in report.risk_level.upper() else
                            C.YELLOW if "HIGH"     in report.risk_level.upper() else C.GREEN)
                report_path = report_dir / f"{report.report_id}.md"
                report_path.write_text(report.report_markdown, encoding="utf-8")
                print(_ok(f"{report.report_id}"))
                print(_data(f"  Facility   : {report.facility_name}"))
                print(_data(f"  Risk level : {risk_col}{report.risk_level}{C.RESET}"))
                print(_data(f"  Saved to   : reports/{report_path.name}"))
                _divider("·")
        else:
            print(_warn("No attributed emissions — skipping report generation."))
            self.results["reports"] = []

        _step_done(t0, f"{len(self.results.get('reports', []))} reports written to /reports")

        # ════════════════════════════════════════════════════════════════════
        # FINAL SUMMARY
        # ════════════════════════════════════════════════════════════════════
        total_elapsed = time.time() - pipeline_start
        print()
        print(_col("═" * width, C.CYAN))
        print(_col(f"  🏁  PIPELINE COMPLETE", C.BOLD + C.WHITE))
        print(_col("═" * width, C.CYAN))

        def _sumrow(label, value, colour=C.WHITE):
            print(f"  {C.DIM}{label:<38}{C.RESET}  {colour}{value}{C.RESET}")

        _sumrow("Sentinel-5P hotspots analysed",  stats['total_hotspots'])
        _sumrow("Super-emitter candidates",        det_summary['above_threshold'], C.YELLOW)
        _sumrow("Satellite tasking requests",       task_summary['total_requests'],  C.CYAN)
        _sumrow("Plumes characterised",             len(plumes),                    C.CYAN)
        _sumrow("Attributed to facilities",         metrics['total_attributed'],    C.GREEN if metrics['total_attributed'] > 0 else C.RED)
        if metrics['total_attributed'] > 0:
            _sumrow("Total attributed emission load", f"{metrics['total_emission_rate_kg_hr']:.1f} kg/hr", C.RED)
            _sumrow("Mean pinpoint accuracy",         f"{metrics['mean_pinpoint_accuracy_m']:.0f} m",      C.GREEN)
        if inversion_results:
            errors = [r.error_pct for r in inversion_results if r.error_pct is not None]
            if errors:
                mean_e = np.mean(errors)
                _sumrow("Plume inversion mean error",    f"{mean_e:.2f}%",           C.GREEN if mean_e < 20 else C.YELLOW)
        _sumrow("Audit reports generated",          len(self.results.get('reports', [])), C.GREEN)
        _sumrow("Total pipeline runtime",           f"{total_elapsed:.2f} s",        C.CYAN)

        print(_col("═" * width, C.CYAN))
        print()

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
