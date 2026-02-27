import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Flame,
  CloudRain,
  MapPin,
  Satellite,
  AlertTriangle,
  Activity,
  Globe,
  TrendingUp,
  RefreshCw,
  Radio,
} from 'lucide-react'
import StatCard from '../components/cards/StatCard'
import {
  EmissionTrendChart,
  RegionalDistributionChart,
  SeverityDistributionChart,
} from '../components/charts/Charts'
import { StatusBadge } from '../components/ui/AlertCard'
import { Spinner } from '../components/ui/Common'
import { dashboardService } from '../services/api'

/**
 * Dashboard Overview Page
 * Main analytics dashboard with stats, charts, and recent activity
 * All data sourced from Django REST Framework backend.
 */
const Dashboard = () => {
  const [summary, setSummary] = useState(null)
  const [trend, setTrend] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchDashboardData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [summaryData, trendData] = await Promise.all([
        dashboardService.getSummary(),
        dashboardService.getTrend(),
      ])
      setSummary(summaryData)
      setTrend(Array.isArray(trendData) ? trendData : [])
    } catch (err) {
      console.error('Dashboard fetch error:', err)
      setError('Failed to load dashboard data. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchDashboardData() }, [])

  // Severity distribution from backend summary counts
  const severityDistribution = (() => {
    const dist = summary?.severity_distribution || {}
    const normalize = (key) => {
      // Backend field is a free-form CharField; try case-insensitive match
      const found = Object.keys(dist).find(
        (k) => k.toLowerCase() === key.toLowerCase()
      )
      return found ? (dist[found] || 0) : 0
    }
    return [
      { name: 'Critical', value: normalize('Critical'), color: '#ef4444' },
      { name: 'High',     value: normalize('High'),     color: '#f97316' },
      { name: 'Medium',   value: normalize('Medium'),   color: '#eab308' },
      { name: 'Low',      value: normalize('Low'),      color: '#22c55e' },
    ]
  })()

  // Facility type distribution → bar chart
  const facilityTypeDistribution = summary?.facility_type_distribution
    ? Object.entries(summary.facility_type_distribution).map(([region, leaks]) => ({
        region,
        leaks,
      }))
    : []

  // Top emitting facilities (already ordered by emission on backend)
  const recentEmitters = (summary?.top_emitters || []).slice(0, 5)

  // Recent reports (last 3 from summary)
  const recentReports = (summary?.recent_reports || []).slice(0, 3)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Spinner size="lg" className="text-accent-green mx-auto mb-4" />
          <p className="text-gray-400">Loading dashboard data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center glass-card p-8">
          <AlertTriangle className="w-12 h-12 text-warning-yellow mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Connection Error</h3>
          <p className="text-gray-400 mb-4">{error}</p>
          <button
            onClick={fetchDashboardData}
            className="inline-flex items-center gap-2 px-4 py-2 bg-accent-green text-white rounded-lg hover:bg-accent-green-dark transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard Overview</h1>
          <p className="text-gray-400 mt-1">
            Real-time methane emission monitoring and analytics
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchDashboardData}
            className="flex items-center gap-2 px-4 py-2 bg-dark-card border border-dark-border rounded-lg hover:border-accent-green transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-400">Refresh</span>
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Facilities"
          value={summary?.total_facilities || 0}
          change={0}
          icon={Flame}
          iconColor="bg-danger-red/20"
          delay={0}
        />
        <StatCard
          title="Detected Hotspots"
          value={summary?.total_detected || 0}
          unit="events"
          change={0}
          icon={CloudRain}
          iconColor="bg-info-blue/20"
          delay={0.1}
        />
        <StatCard
          title="Critical Hotspots"
          value={summary?.critical_hotspots || 0}
          change={0}
          icon={MapPin}
          iconColor="bg-warning-yellow/20"
          delay={0.2}
        />
        <StatCard
          title="Audit Reports"
          value={summary?.total_reports || 0}
          change={0}
          icon={Satellite}
          iconColor="bg-accent-green/20"
          delay={0.3}
        />
      </div>

      {/* Charts Row - Emission Trend full-width */}
      <div className="grid grid-cols-1 gap-6">
        {trend.length > 0 ? (
          <EmissionTrendChart data={trend} />
        ) : (
          <div className="chart-container flex items-center justify-center h-[320px]">
            <div className="text-center">
              <Radio className="w-8 h-8 text-gray-600 mx-auto mb-2" />
              <p className="text-gray-500 text-sm">No emission trend data yet – run the pipeline first.</p>
            </div>
          </div>
        )}
      </div>

      {/* Charts Row - Facility Type + Severity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {facilityTypeDistribution.length > 0 ? (
          <RegionalDistributionChart
            data={facilityTypeDistribution}
            title="Facility Distribution by Type"
            subtitle="Number of facilities per infrastructure type"
          />
        ) : (
          <div className="chart-container flex items-center justify-center h-[380px]">
            <p className="text-gray-500 text-sm">No facility data available yet. Run the pipeline first.</p>
          </div>
        )}
        <SeverityDistributionChart data={severityDistribution} />
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Emitting Facilities */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="glass-card"
        >
          <div className="p-4 border-b border-dark-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-danger-red" />
                <h3 className="font-semibold text-white">Top Emitting Facilities</h3>
              </div>
              <Link
                to="/dashboard/super-emitters"
                className="text-sm text-accent-green hover:underline"
              >
                View All
              </Link>
            </div>
          </div>
          <div className="divide-y divide-dark-border/50">
            {recentEmitters.length > 0 ? recentEmitters.map((facility) => (
              <div
                key={facility.facility_id || facility.id}
                className="p-4 hover:bg-dark-border/20 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-white">
                      {facility.name}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {facility.type} • {facility.state}, {facility.country}
                    </p>
                  </div>
                  <StatusBadge status={facility.status || 'Active'} />
                </div>
              </div>
            )) : (
              <div className="p-8 text-center text-gray-500">
                <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No data yet – run the pipeline</p>
              </div>
            )}
          </div>
        </motion.div>

        {/* Recent Reports */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="glass-card"
        >
          <div className="p-4 border-b border-dark-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-accent-green" />
                <h3 className="font-semibold text-white">Recent Reports</h3>
              </div>
              <Link
                to="/dashboard/reports"
                className="text-sm text-accent-green hover:underline"
              >
                View All
              </Link>
            </div>
          </div>
          <div className="divide-y divide-dark-border/50">
            {recentReports.length > 0 ? recentReports.map((report) => (
              <div
                key={report.report_id || report.id}
                className="p-4 hover:bg-dark-border/20 transition-colors cursor-pointer"
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`w-2 h-2 mt-2 rounded-full flex-shrink-0 ${
                      report.risk_level?.toUpperCase() === 'CRITICAL'
                        ? 'bg-danger-red'
                        : report.risk_level?.toUpperCase() === 'HIGH'
                        ? 'bg-warning-yellow'
                        : 'bg-info-blue'
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">
                      {report.report_id}
                    </p>
                    <p className="text-xs text-gray-500 mt-1 truncate">
                      Risk: {report.risk_level} • {report.facility_name || 'N/A'}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      {report.generated_at ? new Date(report.generated_at).toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      }) : ''}
                    </p>
                  </div>
                </div>
              </div>
            )) : (
              <div className="p-8 text-center text-gray-500">
                <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No reports yet</p>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Bottom Stats Bar */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.7 }}
        className="glass-card p-4"
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-green/20 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-accent-green" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Total Plumes</p>
              <p className="text-lg font-semibold text-white">{summary?.total_plumes || 0}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-info-blue/20 flex items-center justify-center">
              <Activity className="w-5 h-5 text-info-blue" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Attributions</p>
              <p className="text-lg font-semibold text-white">{summary?.total_attributions || 0}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-warning-yellow/20 flex items-center justify-center">
              <Radio className="w-5 h-5 text-warning-yellow" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Tasking Requests</p>
              <p className="text-lg font-semibold text-white">{summary?.total_tasking_requests || 0}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <Globe className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Pipeline Runs</p>
              <p className="text-lg font-semibold text-white">{summary?.total_pipeline_runs || 0}</p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default Dashboard
