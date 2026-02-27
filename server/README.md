# Methane Shadow Hunter - Django REST API Backend

Production-ready REST API for the Methane Shadow Hunter methane detection and attribution system.

## Features

- **9 Django models** mapped to MySQL: Facilities, Hotspots, Plumes, Attributions, Inversions, Reports, etc.
- **Full CRUD + filtering** via Django REST Framework ViewSets
- **Pipeline trigger endpoint** that runs the complete detection pipeline and stores results
- **Dashboard summary** with aggregated metrics for the React frontend
- **GeoJSON export** endpoints for map rendering
- **CORS enabled** for React/Vite frontend communication
- **Optimized inversion logic** with adaptive initial Q estimation, observation scaling, and convergence fixes

---

## Setup

### 1. Install Dependencies

```bash
cd server
pip install -r ../requirements.txt
```

**Required packages:**
- `django>=5.2`
- `djangorestframework>=3.15.0`
- `django-cors-headers>=4.3.0`
- `django-filter>=24.0`
- `mysqlclient>=2.2.0`
- `python-dotenv>=1.0.0`

### 2. Configure Database

Create MySQL database:

```bash
mysql -u root -p"your_password" -e "CREATE DATABASE IF NOT EXISTS methane_shadow_hunter CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Update `.env` in project root (optional, defaults work):

```env
# Database
DB_NAME=methane_shadow_hunter
DB_USER=root
DB_PASSWORD=zoro@1324
DB_HOST=localhost
DB_PORT=3306

# Django
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# CORS (React frontend)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173
```

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Seed Demo Data

Load facilities (55) and methane hotspots (172) from CSV files:

```bash
python manage.py seed_data

# Or clear existing data first:
python manage.py seed_data --clear
```

### 5. (Optional) Create Admin User

```bash
python manage.py createsuperuser
```

### 6. Start Server

```bash
python manage.py runserver
```

API available at: `http://localhost:8000`

---

## API Endpoints

### Facilities

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/facilities/` | List all facilities with filters |
| GET | `/api/facilities/{id}/` | Facility detail |
| POST | `/api/facilities/` | Create new facility |
| GET | `/api/facilities/by_type/` | Count by type |
| GET | `/api/facilities/by_operator/` | Count by operator |
| GET | `/api/facilities/nearby/?lat=&lon=&radius_km=` | Geo search |

**Query params:** `?type=refinery&operator=ONGC&search=terminal&ordering=name`

### Hotspots & Detections

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/hotspots/` | Raw Sentinel-5P observations |
| GET | `/api/hotspots/stats/` | Summary statistics |
| GET | `/api/detected-hotspots/` | Anomaly-filtered hotspots |

### Plumes & Attributions

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/plumes/` | CarbonMapper plume observations |
| GET | `/api/attributions/` | Spatial join results (plume→facility) |
| GET | `/api/attributions/{id}/` | Attribution detail with facility & plume |
| GET | `/api/attributions/metrics/` | Pinpoint accuracy metrics |

### Inversion Results

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/inversions/` | Gaussian plume inversion results |
| GET | `/api/inversions/accuracy/` | Emission rate error metrics |

### Reports & Pipeline

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/reports/` | Compliance audit reports (list) |
| GET | `/api/reports/{id}/` | Full report with markdown |
| POST | `/api/pipeline/trigger/` | **Trigger pipeline execution** |
| GET | `/api/pipeline-runs/` | Pipeline execution history |
| GET | `/api/pipeline-runs/{id}/results/` | Full run results |

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboard/summary/` | Aggregated metrics for dashboard |

### GeoJSON Exports

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/geojson/facilities/` | Facilities as GeoJSON FeatureCollection |
| GET | `/api/geojson/hotspots/` | Hotspots as GeoJSON |
| GET | `/api/geojson/attributions/` | Plume→facility lines as GeoJSON |

---

## Usage Example: Trigger Pipeline

Run the methane detection pipeline and store all results in MySQL:

```bash
# Demo mode (offline data, no LLM)
POST /api/pipeline/trigger/
Content-Type: application/json

{
  "mode": "demo",
  "use_llm": false
}
```

```bash
# Live mode (GEE + Open-Meteo + live wind)
POST /api/pipeline/trigger/
Content-Type: application/json

{
  "mode": "live",
  "use_llm": false
}
```

**Response:**

```json
{
  "id": 1,
  "mode": "demo",
  "use_llm": false,
  "status": "completed",
  "total_hotspots": 122,
  "detected_hotspots_count": 40,
  "plumes_count": 40,
  "attributions_count": 14,
  "reports_count": 0,
  "error_message": "",
  "started_at": "2026-02-27T10:30:00Z",
  "completed_at": "2026-02-27T10:32:15Z"
}
```

Then query results:

```bash
# Get all attributions from this run
GET /api/attributions/?pipeline_run=1

# Get dashboard summary
GET /api/dashboard/summary/

# Get inversion accuracy metrics
GET /api/inversions/accuracy/?pipeline_run=1
```

---

## Inversion Fix Applied (Feb 2026)

The Django backend now uses the same optimized inversion logic as the core pipeline:

### Before (Broken)
- All estimates = 36.0 kg/hr (stuck at initial guess)  
- CI: `[0.0, inf]` (overflow)  
- Mean error: **64.63%**

### After (Fixed)
- Adaptive initial Q estimation from peak concentration  
- Observation scaling to prevent vanishing gradients  
- Learning rate: 0.01 → **0.1** with ReduceLROnPlateau scheduler  
- Warm-up: 300 iterations before convergence check  
- Relative convergence criterion  
- CI clamping to prevent overflow  
- Varied receptor layouts per emitter  
- Mean error: **~40%**

### Changes in `server/api/views.py`

The `_run_and_store_inversions` function now:

1. Uses `inverter.create_synthetic_observation()` instead of manual grid creation
2. Passes `wind_data.speed_ms` (not `.speed`) for consistency
3. Uses `wind_data.stability_class` for proper dispersion coefficients
4. Increased receptors from 50 → **200** for better conditioning
5. Increased domain from 500m → **3000m** for realistic plume extent

All fixes from `src/plume/inversion.py` automatically apply.

---

## Admin Interface

Access Django admin at `http://localhost:8000/admin/` to:

- Browse all database records  
- Inspect pipeline runs  
- View/edit facilities and reports  
- Export data as CSV

---

## React Frontend Integration

The API is pre-configured with CORS for `localhost:3000` (Create React App) and `localhost:5173` (Vite).

**Example React fetch:**

```javascript
// Trigger pipeline
const response = await fetch('http://localhost:8000/api/pipeline/trigger/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ mode: 'demo', use_llm: false })
});
const run = await response.json();

// Poll for completion
const pollRun = async (runId) => {
  const res = await fetch(`http://localhost:8000/api/pipeline-runs/${runId}/`);
  const data = await res.json();
  if (data.status === 'completed') {
    // Fetch results
    const dashboard = await fetch('http://localhost:8000/api/dashboard/summary/');
    // Render dashboard
  }
};
```

---

## Testing

```bash
# Run Django tests
python manage.py test api

# Check API with curl
curl http://localhost:8000/api/facilities/ | jq
curl http://localhost:8000/api/dashboard/summary/ | jq

# Trigger pipeline
curl -X POST http://localhost:8000/api/pipeline/trigger/ \
  -H "Content-Type: application/json" \
  -d '{"mode": "demo", "use_llm": false}' | jq
```

---

## Production Deployment

1. Set `DEBUG=False` in `.env`
2. Use a proper `SECRET_KEY` (generate with `django.core.management.utils.get_random_secret_key()`)
3. Configure `ALLOWED_HOSTS` for your domain
4. Use Gunicorn/uWSGI with Nginx
5. Set up MySQL backups
6. Use environment variables for all secrets

```bash
# Example production command
gunicorn server.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

---

## Troubleshooting

### MySQL connection error

```
django.db.utils.OperationalError: (2003, "Can't connect to MySQL server")
```

→ Check MySQL is running: `mysql -u root -p`  
→ Verify credentials in `.env`  
→ Create database: `CREATE DATABASE methane_shadow_hunter;`

### Import error: No module named 'src'

```
ModuleNotFoundError: No module named 'src'
```

→ The Django server needs the project root in Python path. This is handled automatically in `views.py`:

```python
project_root = str(settings.PROJECT_ROOT)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
```

### WindData has no attribute 'speed'

→ Fixed in Feb 2026. The code now uses `wind_data.speed_ms` (correct attribute).

---

## License

Same as main project.
