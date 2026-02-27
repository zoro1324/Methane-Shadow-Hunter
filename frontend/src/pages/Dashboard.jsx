import { motion } from 'framer-motion'
import {
  Flame,
  CloudRain,
  MapPin,
  TrendingUp,
  AlertTriangle,
  Clock,
  Activity,
  Globe,
} from 'lucide-react'
import StatCard from '../components/cards/StatCard'
import {
  EmissionTrendChart,
  RegionalDistributionChart,
  SeverityDistributionChart,
} from '../components/charts/Charts'
import { StatusBadge } from '../components/ui/AlertCard'
import {
  dashboardStats,
  emissionTrends,
  regionalDistribution,
  severityDistribution,
  superEmitters,
  alerts,
} from '../data/mockData'

/**
 * Dashboard Overview Page
 * Main analytics dashboard with stats, charts, and recent activity
 */
const Dashboard = () => {
  // Recent super emitters for quick view
  const recentEmitters = superEmitters.slice(0, 5)
  
  // Recent alerts for quick view
  const recentAlerts = alerts.filter(a => !a.read).slice(0, 3)

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
          <div className="flex items-center gap-2 px-4 py-2 bg-dark-card border border-dark-border rounded-lg">
            <Clock className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-400">
              Last updated: {dashboardStats.lastUpdate}
            </span>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Active Leaks"
          value={dashboardStats.activeLeaks}
          change={dashboardStats.activeLeaksChange}
          icon={Flame}
          iconColor="bg-danger-red/20"
          delay={0}
        />
        <StatCard
          title="CO₂ Equivalent Impact"
          value={dashboardStats.co2Equivalent}
          unit={dashboardStats.co2EquivalentUnit}
          change={dashboardStats.co2EquivalentChange}
          icon={CloudRain}
          iconColor="bg-info-blue/20"
          delay={0.1}
        />
        <StatCard
          title="High-Risk Zones"
          value={dashboardStats.highRiskZones}
          change={dashboardStats.highRiskZonesChange}
          icon={MapPin}
          iconColor="bg-warning-yellow/20"
          delay={0.2}
        />
        <StatCard
          title="Detection Accuracy"
          value="94.2%"
          change={+2.1}
          icon={TrendingUp}
          iconColor="bg-accent-green/20"
          delay={0.3}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <EmissionTrendChart data={emissionTrends} />
        <RegionalDistributionChart data={regionalDistribution} />
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Severity Chart */}
        <SeverityDistributionChart data={severityDistribution} />

        {/* Recent Super Emitters */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="glass-card lg:col-span-1"
        >
          <div className="p-4 border-b border-dark-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-danger-red" />
                <h3 className="font-semibold text-white">Recent Super Emitters</h3>
              </div>
              <a
                href="/dashboard/super-emitters"
                className="text-sm text-accent-green hover:underline"
              >
                View All
              </a>
            </div>
          </div>
          <div className="divide-y divide-dark-border/50">
            {recentEmitters.map((emitter) => (
              <div
                key={emitter.id}
                className="p-4 hover:bg-dark-border/20 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-white">
                      {emitter.location}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {emitter.emissionRate} {emitter.unit} • {emitter.riskLevel}
                    </p>
                  </div>
                  <StatusBadge status={emitter.status} />
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Recent Alerts */}
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
                <h3 className="font-semibold text-white">Recent Alerts</h3>
              </div>
              <a
                href="/dashboard/alerts"
                className="text-sm text-accent-green hover:underline"
              >
                View All
              </a>
            </div>
          </div>
          <div className="divide-y divide-dark-border/50">
            {recentAlerts.map((alert) => (
              <div
                key={alert.id}
                className="p-4 hover:bg-dark-border/20 transition-colors cursor-pointer"
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`w-2 h-2 mt-2 rounded-full flex-shrink-0 ${
                      alert.type === 'critical'
                        ? 'bg-danger-red'
                        : alert.type === 'warning'
                        ? 'bg-warning-yellow'
                        : 'bg-info-blue'
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">
                      {alert.title}
                    </p>
                    <p className="text-xs text-gray-500 mt-1 truncate">
                      {alert.message}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      {new Date(alert.timestamp).toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            {recentAlerts.length === 0 && (
              <div className="p-8 text-center text-gray-500">
                <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No unread alerts</p>
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
              <p className="text-xs text-gray-500">Detection Rate</p>
              <p className="text-lg font-semibold text-white">94.2%</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-info-blue/20 flex items-center justify-center">
              <Activity className="w-5 h-5 text-info-blue" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Resolution Rate</p>
              <p className="text-lg font-semibold text-white">78.5%</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-warning-yellow/20 flex items-center justify-center">
              <Clock className="w-5 h-5 text-warning-yellow" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Avg Response Time</p>
              <p className="text-lg font-semibold text-white">4.2 hrs</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <Globe className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Coverage Area</p>
              <p className="text-lg font-semibold text-white">India</p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default Dashboard
