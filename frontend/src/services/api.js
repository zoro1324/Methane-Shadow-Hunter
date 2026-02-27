import axios from 'axios'

/**
 * API Service
 * Centralized API configuration and service methods
 * Currently uses mock data, but structured for easy backend integration
 */

// Base API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for auth tokens
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      localStorage.removeItem('authToken')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

/**
 * Emissions Service
 */
export const emissionsService = {
  // Get emission trends data
  getTrends: async (params = {}) => {
    const response = await apiClient.get('/emissions/trends', { params })
    return response.data
  },

  // Get regional distribution
  getRegionalDistribution: async () => {
    const response = await apiClient.get('/emissions/regions')
    return response.data
  },

  // Get severity distribution
  getSeverityDistribution: async () => {
    const response = await apiClient.get('/emissions/severity')
    return response.data
  },

  // Get dashboard stats
  getDashboardStats: async () => {
    const response = await apiClient.get('/dashboard/stats')
    return response.data
  },
}

/**
 * Super Emitters Service
 */
export const superEmittersService = {
  // Get all super emitters
  getAll: async (params = {}) => {
    const response = await apiClient.get('/super-emitters', { params })
    return response.data
  },

  // Get single super emitter by ID
  getById: async (id) => {
    const response = await apiClient.get(`/super-emitters/${id}`)
    return response.data
  },

  // Update super emitter status
  updateStatus: async (id, status) => {
    const response = await apiClient.patch(`/super-emitters/${id}/status`, { status })
    return response.data
  },

  // Create investigation
  createInvestigation: async (id, data) => {
    const response = await apiClient.post(`/super-emitters/${id}/investigate`, data)
    return response.data
  },
}

/**
 * Map Service
 */
export const mapService = {
  // Get map markers
  getMarkers: async (bounds = null) => {
    const params = bounds ? { bounds: JSON.stringify(bounds) } : {}
    const response = await apiClient.get('/map/markers', { params })
    return response.data
  },

  // Get heatmap data
  getHeatmapData: async () => {
    const response = await apiClient.get('/map/heatmap')
    return response.data
  },
}

/**
 * Alerts Service
 */
export const alertsService = {
  // Get all alerts
  getAll: async (params = {}) => {
    const response = await apiClient.get('/alerts', { params })
    return response.data
  },

  // Mark alert as read
  markAsRead: async (id) => {
    const response = await apiClient.patch(`/alerts/${id}/read`)
    return response.data
  },

  // Mark all as read
  markAllAsRead: async () => {
    const response = await apiClient.patch('/alerts/read-all')
    return response.data
  },

  // Delete alert
  delete: async (id) => {
    const response = await apiClient.delete(`/alerts/${id}`)
    return response.data
  },

  // Get notification preferences
  getPreferences: async () => {
    const response = await apiClient.get('/alerts/preferences')
    return response.data
  },

  // Update notification preferences
  updatePreferences: async (preferences) => {
    const response = await apiClient.put('/alerts/preferences', preferences)
    return response.data
  },
}

/**
 * Reports Service
 */
export const reportsService = {
  // Get all reports
  getAll: async () => {
    const response = await apiClient.get('/reports')
    return response.data
  },

  // Get single report
  getById: async (id) => {
    const response = await apiClient.get(`/reports/${id}`)
    return response.data
  },

  // Download report PDF
  downloadPdf: async (id) => {
    const response = await apiClient.get(`/reports/${id}/download`, {
      responseType: 'blob',
    })
    return response.data
  },

  // Generate custom report
  generateCustom: async (params) => {
    const response = await apiClient.post('/reports/generate', params)
    return response.data
  },

  // Export data
  exportData: async (format, params = {}) => {
    const response = await apiClient.get(`/reports/export/${format}`, {
      params,
      responseType: 'blob',
    })
    return response.data
  },
}

/**
 * Satellites Service
 */
export const satellitesService = {
  // Get satellite status
  getStatus: async () => {
    const response = await apiClient.get('/satellites/status')
    return response.data
  },

  // Get satellite passes
  getPasses: async (params = {}) => {
    const response = await apiClient.get('/satellites/passes', { params })
    return response.data
  },
}

/**
 * Auth Service
 */
export const authService = {
  // Login
  login: async (credentials) => {
    const response = await apiClient.post('/auth/login', credentials)
    if (response.data.token) {
      localStorage.setItem('authToken', response.data.token)
    }
    return response.data
  },

  // Logout
  logout: () => {
    localStorage.removeItem('authToken')
  },

  // Get current user
  getCurrentUser: async () => {
    const response = await apiClient.get('/auth/me')
    return response.data
  },

  // Update profile
  updateProfile: async (data) => {
    const response = await apiClient.put('/auth/profile', data)
    return response.data
  },
}

export default apiClient
