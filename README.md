# 🛰️ Methane Shadow Hunter

A full-stack, AI-driven satellite pipeline to detect, attribute, quantify, and report on global methane "super-emitters."

This project fuses multiple layers of environmental data—from low-resolution global satellite scans down to high-resolution targeted imagery. It then applies **PyTorch**-based inversion modeling to mathematically calculate the severity of the leak (in kg/hr), and finally uses a **LangChain+Ollama** AI Agent to autonomously write a formal compliance audit report holding the responsible facility accountable.

---

## 🏗️ Architecture & Tech Stack

This project is built using modern Python libraries, broken down into specific modular domains. Here is exactly what each technology does in the pipeline:

### 1. Data Ingestion & Orchestration Layer
* **`pandas` & `numpy`**: The backbone of the data ingestion. Used to load the initial metadata, process CSVs containing raw Sentinel-5P hotspots, and handle high-speed arrays for mathematical anomaly detection.
* **`pystac-client` & `requests`**: Connects directly to the **CarbonMapper STAC AI Catalog**. STAC (SpatioTemporal Asset Catalog) is the modern standard for querying Earth observation data. We use this to retrieve high-resolution plume data using bounding boxes (AOIs).
* **`rasterio`** *(optional but recommended for live data)*: Essential for reading and extracting specific pixel values from the raw GeoTIFF satellite files (like our `India_Methane_Map.tif`).

### 2. Multi-Scale Data Fusion (Geospatial)
* **`geopandas` & `shapely`**: These are used for the **Spatial Join** module. When the system detects a high-res plume, it needs to know "who is responsible?". We use these libraries to load a vector database of known Oil & Gas infrastructure and mathematically calculate the *Haversine distance* to map the plume to the closest facility with high pinpoint accuracy.

### 3. Plume Inversion AI Modeling
* **`torch` (PyTorch)**: The most complex mathematical component. Just seeing a gas cloud isn't enough; we need to know the emission rate. We built a **Differentiable Gaussian Plume Forward Model**. By utilizing PyTorch's automatic differentiation (`autograd`), we can run an inverse optimization loop (using the Adam optimizer and Mean Squared Error loss). The AI looks at the shape/concentration of the plume, factors in wind speed, and mathematically reverse-engineers the exact emission rate `Q` (kg/hr).
* **`scipy` / `numpy`**: Used alongside PyTorch to handle Pasquill-Gifford atmospheric stability class coefficients.

### 4. Autonomous Compliance Reporting (LLM Agent)
* **`langchain`**: The orchestration framework for our AI Agent. We use LangChain to construct a "tool-using" agent. Instead of just writing a generic summary, LangChain allows the AI to execute specific Python functions (like `facility_lookup` or `search_regulations`) to gather real facts before it writes.
* **`langchain-ollama`**: Connects LangChain to a locally hosted Large Language Model (like `llama3:8b`). We use Ollama so that this sensitive environmental compliance auditing can run entirely offline without paying for API tokens or sending data to third parties.

---

## 🚀 How to Run the Pipeline

### 1. Identify Your Mode
The system can run in two modes controlled by the `.env` file:
* `USE_DEMO_DATA=true` (Pre-loaded Offline Data)
* `USE_DEMO_DATA=false` (Live API Connection)

### 2. Install Dependencies
Ensure you have the required packages:
```bash
pip install -r requirements.txt
```
*(Note: If you plan to use live Google Earth Engine data later, you will also need to `pip install earthengine-api` and authenticate).*

### 3. Start your Local LLM (Required for AI Audit Reports)
The final step of the pipeline generates a report. Ensure your Ollama server is running in the background:
```bash
ollama run llama3:8b
# Leave this terminal open!
```

### 4. Execute the Pipeline
Run the main orchestrator script:
```bash
python src/pipeline.py
```
* **What you will see:** A beautifully formatted terminal output tracking through all 7 steps: Loading Sentinel data -> Finding Anomalies -> Simulating Tasking -> CarbonMapper integration -> Infrastructure Attribution -> PyTorch Inversion -> LangChain Report Generation.
* **The Result:** Check the `reports/` folder for a newly generated `.md` compliance audit.

Alternatively, you can interactively explore the math and logic step-by-step using the Jupyter notebook:
```bash
jupyter notebook demo_pipeline.ipynb
```

---

## 📁 Repository Structure

*   `src/data/`: Modules to fetch Sentinel-5P hotspots, CarbonMapper STAC catalogs, and Oil & Gas infrastructure.
*   `src/fusion/`: The logic to detect anomalies, task high-res satellites, and spatially join plumes to facilities.
*   `src/plume/`: The PyTorch Gaussian Plume equations and inverse modeling optimizer matrix.
*   `src/agent/`: The LangChain tools, prompts, and Ollama agent executor.
*   `models/dataset/`: Essential pre-loaded geospatial data for offline demonstration (India context).
*   `reports/`: Where the LLM drops the finished `.md` compliance audits.
