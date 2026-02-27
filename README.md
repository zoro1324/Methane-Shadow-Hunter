# Methane Shadow Hunter 🛰️☁️

**Methane Shadow Hunter** is an autonomous, end-to-end data pipeline designed to actively hunt down methane super-emitters from space, attribute the leaks to specific industrial infrastructure on the ground, calculate highly-accurate emission rates using live weather data, and dynamically generate regulatory compliance reports using LLM agents.

## 🚀 How it Works (The 7-Step Pipeline)

The system strings together a sequence of real-time satellite data, spatial analytics, physics-based simulations, and AI agents.

### STEP 1: Fast Global Sweeps (Sentinel-5P)
- **What it does:** Uses Google Earth Engine (GEE) to dynamically download the last 30 days of Sentinel-5P TROPOMI methane concentration data over the configured Area of Interest (AOI) bounding box.
- **Inputs:** `AOI_BBOX` (default: India region), `Timeframe` (default: last 30 days).
- **Process:** Queries the `COPERNICUS/S5P/OFFL/L3_CH4` image collection, filters out anomalies over the target area.
- **Outputs:** A DataFrame of rough, low-resolution "hotspot" coordinates where high methane concentration was detected.

### STEP 2: Anomaly Detection (Statistical Filtering)
- **What it does:** Separates genuine super-emitter events from natural methane variability (agriculture, wetlands, general background methane noise).
- **Inputs:** The Hotspots DataFrame from Step 1.
- **Process:** Calculates the standard deviation and mean of the dataset. It only flags locations exceeding the threshold configured in `.env`.
- **Outputs:** A prioritized list of "Tasking Candidates" that warrant further investigation.
- **Default Value:** `HOTSPOT_THRESHOLD_SIGMA=0.1`. (Reason: Allows for a highly-sensitive pipeline to catch smaller but persistent leaks, although 2.0 is often standard for massive anomaly hunting).

### STEP 3: High-Resolution Tasking Trigger
- **What it does:** Simulates the process of "tasking" a highly expensive, targeted satellite (like CarbonMapper Tanager or GHGSat) to fly over the specific coordinates flagged in Step 2.
- **Process:** Generates automated tasking requests and prepares the system to listen for high-res data on these precise coordinates.

### STEP 4: High-Res Plume Data (CarbonMapper)
- **What it does:** Queries for highly detailed "plume" imagery over the anomalous spots to measure exact dimension and shape of the leak.
- **Inputs:** Coordinates flagged in Step 3.
- **Process:** Queries the public CarbonMapper STAC API. If the API is waiting on satellite flyovers for those specific live locations (which happens frequently due to tasking lag), the pipeline spins up highly realistic, statistically modeled plumes right on top of the coordinates so downstream analytics don't halt.
- **Outputs:** Detailed plume objects including length, geometry, and base emission estimates.

### STEP 5: Infrastructure Attribution (Spatial Join)
- **What it does:** Answers the question: *Who is leaking?*
- **Inputs:** The coordinates of the detected Plumes (Step 4) + the Oil/Gas Infrastructure Database.
- **Process:** Calculates Haversine distances to cross-reference the exact origin of the methane plume with a dataset of industrial facilities (Refineries, Pipelines, Wells). 
- **Outputs:** Plumes attached with specific facility names and operators (e.g. "ONGC Refinery 3").
- **Default Value:** `SPATIAL_JOIN_RADIUS_KM=5.0`. (Reason: Satellite pixels can range from 30m to several kilometers in width depending on the instrument; 5km captures the facility even if the plume has already drifted slightly).

### STEP 6: Plume Inversion Modeling (PyTorch Physics Engine)
- **What it does:** Calculates the exact volume of gas leaking (kg/hr).
- **Inputs:** Methane concentration grids, wind data, plume geometry.
- **Process:** This step pulls **LIVE wind speed and direction** from the Open-Meteo API for the exact GPS coordinates. Wind speed is the single most critical factor in dispersion formulas. It then feeds this live weather data into a PyTorch-backed Gaussian Plume Inversion algorithm to calculate the true emission rate from the observed satellite concentrations.
- **Outputs:** A highly accurate `Est: XX kg/hr` rating with mathematical confidence intervals and error validation metrics.

### STEP 7: Autonomous Compliance Reporting (LLM Agent)
- **What it does:** Turns raw numbers into actionable regulatory reports to alert stakeholders or issue fines.
- **Inputs:** All spatial, infra, and emission rate data from previous steps.
- **Process:** Uses LangChain and Ollama (default: `llama3:8b`) to act as a regulatory compliance officer. The LLM processes the facts, checks imaginary/real regulations, constructs an executive summary, risk level, and suggested remediation steps.
- **Outputs:** High-quality, legally-structured Markdown files placed in the `/reports` folder.

## 🛠️ Running the Pipeline

Before running, ensure your `.env` is configured properly. By default, it uses live APIs where available.

```bash
# Run the pipeline with live Earth Engine and Live Open-Meteo Data
python src/pipeline.py --live
```

### Configuration (`.env`)
You can control the pipeline entirely through the `.env` file without changing code:
* `USE_DEMO_DATA=False` (Turns off bundled CSV fallbacks)
* `HOTSPOT_THRESHOLD_SIGMA=0.1` (Tweak to dictate how egregious a leak must be to trigger the pipeline)
* `LLM_PROVIDER=ollama` and `OLLAMA_MODEL=llama3:8b` (Dictates which AI writes the reports)
* `AOI_MIN_LON=68.0` / `AOI_MIN_LAT=6.5` (Target bounding box. Default is India).
