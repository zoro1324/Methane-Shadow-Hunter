import axios from 'axios'

/**
 * API Service – wired to Django REST Framework backend
 * Base URL: http://localhost:8000/api
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// ─── Request / Response interceptors ─────────────────────────────────────
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error),
)

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken')
    }
    return Promise.reject(error)
  },
)

// ─── Helper: unwrap paginated DRF response ───────────────────────────────
const unwrap = (res) => {
  // DRF pagination wraps results in { count, next, previous, results }
  if (res.data?.results !== undefined) return res.data.results
  return res.data
}

// ─── Dashboard ───────────────────────────────────────────────────────────
export const dashboardService = {
  getSummary: async () => {
    const res = await apiClient.get('/dashboard/summary/')
    return res.data
  },
  getTrend: async () => {
    const res = await apiClient.get('/dashboard/trend/')
    return res.data
  },
}

// ─── Facilities ──────────────────────────────────────────────────────────
export const facilitiesService = {
  getAll: async (params = {}) => {
    const res = await apiClient.get('/facilities/', { params })
    return unwrap(res)
  },
  getById: async (id) => {
    const res = await apiClient.get(`/facilities/${id}/`)
    return res.data
  },
  getByType: async () => {
    const res = await apiClient.get('/facilities/by_type/')
    return res.data
  },
  getNearby: async (lat, lon, radius = 50) => {
    const res = await apiClient.get('/facilities/nearby/', { params: { lat, lon, radius } })
    return res.data
  },
  /** Search facilities by name / operator (uses DRF SearchFilter) */
  search: async (query) => {
    const res = await apiClient.get('/facilities/', { params: { search: query, page_size: 50 } })
    return unwrap(res)
  },
}

// ─── Heatmap Fallback (DB-sourced, when GEE is unavailable) ──────────────
export const heatmapFallbackService = {
  getPoints: async () => {
    const res = await apiClient.get('/heatmap/fallback/')
    return res.data
  },
}

// ─── Hotspots (Sentinel-5P) ──────────────────────────────────────────────
export const hotspotsService = {
  getAll: async (params = {}) => {
    const res = await apiClient.get('/hotspots/', { params })
    return unwrap(res)
  },
  getStats: async () => {
    const res = await apiClient.get('/hotspots/stats/')
    return res.data
  },
}

// ─── Detected Hotspots ───────────────────────────────────────────────────
export const detectedHotspotsService = {
  getAll: async (params = {}) => {
    const res = await apiClient.get('/detected-hotspots/', { params })
    return unwrap(res)
  },
}

// ─── Plume Observations ──────────────────────────────────────────────────
export const plumesService = {
  getAll: async (params = {}) => {
    const res = await apiClient.get('/plumes/', { params })
    return unwrap(res)
  },
}

// ─── Attributed Emissions ────────────────────────────────────────────────
export const attributionsService = {
  getAll: async (params = {}) => {
    const res = await apiClient.get('/attributions/', { params })
    return unwrap(res)
  },
  getMetrics: async () => {
    const res = await apiClient.get('/attributions/metrics/')
    return res.data
  },
}

// ─── Inversion Results ───────────────────────────────────────────────────
export const inversionsService = {
  getAll: async (params = {}) => {
    const res = await apiClient.get('/inversions/', { params })
    return unwrap(res)
  },
  getAccuracy: async () => {
    const res = await apiClient.get('/inversions/accuracy/')
    return res.data
  },
}

// ─── Tasking Requests ────────────────────────────────────────────────────
export const taskingService = {
  getAll: async (params = {}) => {
    const res = await apiClient.get('/tasking-requests/', { params })
    return unwrap(res)
  },
}

// ─── Audit Reports ───────────────────────────────────────────────────────
export const reportsService = {
  getAll: async (params = {}) => {
    const res = await apiClient.get('/reports/', { params })
    return unwrap(res)
  },
  getById: async (id) => {
    const res = await apiClient.get(`/reports/${id}/`)
    return res.data
  },
}

// ─── Pipeline ────────────────────────────────────────────────────────────
export const pipelineService = {
  getRuns: async (params = {}) => {
    const res = await apiClient.get('/pipeline-runs/', { params })
    return unwrap(res)
  },
  trigger: async (mode = 'demo', use_llm = true) => {
    // Returns 202 immediately with { run_id, status: 'running' }
    const res = await apiClient.post('/pipeline/trigger/', { mode, use_llm })
    return res.data
  },
  pollRun: async (runId, { onProgress, intervalMs = 3000, timeoutMs = 600000 } = {}) => {
    // Poll GET /api/pipeline-runs/{id}/ until status is completed or failed
    return new Promise((resolve, reject) => {
      const deadline = Date.now() + timeoutMs
      const tick = async () => {
        try {
          const res = await apiClient.get(`/pipeline-runs/${runId}/`)
          const run = res.data
          if (onProgress) onProgress(run)
          if (run.status === 'completed') return resolve(run)
          if (run.status === 'failed')    return reject(new Error(run.error_message || 'Pipeline failed'))
          if (Date.now() > deadline)      return reject(new Error('Pipeline timed out'))
          setTimeout(tick, intervalMs)
        } catch (err) {
          reject(err)
        }
      }
      setTimeout(tick, intervalMs)
    })
  },
  getRunResults: async (id) => {
    const res = await apiClient.get(`/pipeline-runs/${id}/results/`)
    return res.data
  },
}

// ─── GeoJSON (for map) ──────────────────────────────────────────────────
export const geojsonService = {
  getFacilities: async () => {
    const res = await apiClient.get('/geojson/facilities/')
    return res.data
  },
  getHotspots: async () => {
    const res = await apiClient.get('/geojson/hotspots/')
    return res.data
  },
  getAttributions: async () => {
    const res = await apiClient.get('/geojson/attributions/')
    return res.data
  },
}

// ─── Google Earth Engine ─────────────────────────────────────────────────
export const geeService = {
  /** Get GEE tile URL for Sentinel-5P CH4 overlay */
  getCH4Tiles: async (days = 30) => {
    const res = await apiClient.get('/gee/ch4-tiles/', { params: { days } })
    return res.data
  },
  /** Get sampled CH4 points as [lat, lng, intensity] for leaflet.heat */
  getCH4Heatmap: async (days = 30, numPoints = 1000, scale = 20000) => {
    const res = await apiClient.get('/gee/ch4-heatmap/', {
      params: { days, num_points: numPoints, scale },
      timeout: 12000,   // fail fast – DB fallback fires in parallel
    })
    return res.data
  },
  /**
   * Detect CH4 anomaly hotspots from Sentinel-5P TROPOMI for a date range.
   * @param {string} startDate  YYYY-MM-DD
   * @param {string} endDate    YYYY-MM-DD
   * @param {number} numPoints  Max sample points (default 1000)
   * @param {number} scale      Sampling resolution in metres (default 20000)
   * @returns {{ hotspots, stats, tile_url, start_date, end_date }}
   */
  getHotspots: async (startDate, endDate, numPoints = 1000, scale = 20000) => {
    const res = await apiClient.get('/gee/ch4-hotspots/', {
      params: { start_date: startDate, end_date: endDate, num_points: numPoints, scale },
      timeout: 120_000,  // GEE calls can take up to ~60 s
    })
    return res.data
  },
  /**
   * Company-centric CH4 analysis. Pass facility_id OR lat/lng,
   * plus radiusKm, startDate, endDate.
   */
  getCompanyAnalysis: async ({ facilityId, lat, lng, radiusKm = 50, startDate, endDate, numPoints = 1000, scale = 10000 } = {}) => {
    const params = { radius_km: radiusKm, start_date: startDate, end_date: endDate, num_points: numPoints, scale }
    if (facilityId) params.facility_id = facilityId
    if (lat != null) params.lat = lat
    if (lng != null) params.lng = lng
    const res = await apiClient.get('/gee/company-analysis/', { params, timeout: 180_000 })
    return res.data
  },
}

// ─── Authentication ──────────────────────────────────────────────────────
export const authService = {
  register: async ({ username, email, password, confirm_password, first_name, last_name }) => {
    const res = await apiClient.post('/auth/register/', {
      username, email, password, confirm_password, first_name, last_name,
    })
    return res.data
  },
  login: async ({ username, password }) => {
    const res = await apiClient.post('/auth/login/', { username, password })
    return res.data
  },
  /** Save token + user info to localStorage */
  saveAuth: (data) => {
    localStorage.setItem('authToken', data.token)
    localStorage.setItem('authUser', JSON.stringify(data.user))
  },
  /** Clear session */
  logout: () => {
    localStorage.removeItem('authToken')
    localStorage.removeItem('authUser')
  },
  /** Check if user is logged in */
  isAuthenticated: () => !!localStorage.getItem('authToken'),
  /** Get stored user */
  getUser: () => {
    try { return JSON.parse(localStorage.getItem('authUser')) } catch { return null }
  },
}

export default apiClient
