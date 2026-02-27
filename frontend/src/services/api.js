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
  trigger: async (mode = 'demo') => {
    const res = await apiClient.post('/pipeline/trigger/', { mode })
    return res.data
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

// ─── Google Earth Engine (heatmap) ───────────────────────────────────────
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
    })
    return res.data
  },
}

export default apiClient
