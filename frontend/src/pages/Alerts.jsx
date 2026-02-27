import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bell,
  CheckCircle,
  AlertTriangle,
  AlertCircle,
  Info,
  Filter,
  Check,
  Trash2,
  Settings,
  Clock,
  RefreshCw,
} from 'lucide-react'
import { AlertCard } from '../components/ui/AlertCard'
import { Button, Spinner } from '../components/ui/Common'
import { detectedHotspotsService, reportsService } from '../services/api'

/**
 * Alerts Page – derived from detected hotspots + audit reports
 */
const Alerts = () => {
  const [alerts, setAlerts] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)

  const fetchAlerts = async () => {
    setLoading(true)
    try {
      const [hotspots, reports] = await Promise.all([
        detectedHotspotsService.getAll({ ordering: '-anomaly_score' }),
        reportsService.getAll({ ordering: '-generated_at' }),
      ])

      const alertList = []
      const hList = Array.isArray(hotspots) ? hotspots : []
      const rList = Array.isArray(reports) ? reports : []

      // Derive alerts from critical/high priority hotspots
      hList.forEach((h, i) => {
        const severity = (h.severity || 'medium').toLowerCase()
        const typeMap = { critical: 'critical', high: 'warning', medium: 'info', low: 'info' }
        alertList.push({
          id: `HS-${h.id || i}`,
          type: typeMap[severity] || 'info',
          title: severity === 'critical' ? 'Critical Hotspot Detected' :
                 severity === 'high' ? 'High-Priority Hotspot' :
                 `Hotspot Detected (${severity})`,
          message: `Anomaly score: ${h.anomaly_score?.toFixed(2) || 'N/A'}, CH₄ count: ${h.ch4_count || 'N/A'}${h.requires_highres ? ' – Requires high-res tasking' : ''}`,
          location: h.hotspot_id || `Lat ${h.latitude?.toFixed(4)}, Lon ${h.longitude?.toFixed(4)}`,
          timestamp: h.detected_at || new Date().toISOString(),
          read: severity !== 'critical' && severity !== 'high',
        })
      })

      // Derive alerts from audit reports
      rList.slice(0, 5).forEach((r) => {
        alertList.push({
          id: `RPT-${r.id}`,
          type: r.risk_level === 'CRITICAL' ? 'critical' : r.risk_level === 'HIGH' ? 'warning' : 'success',
          title: `Report Generated: ${r.report_id}`,
          message: `Risk level: ${r.risk_level}${r.facility_name ? ` for ${r.facility_name}` : ''}`,
          location: r.facility_name || 'N/A',
          timestamp: r.generated_at || new Date().toISOString(),
          read: true,
        })
      })

      setAlerts(alertList)
    } catch (err) {
      console.error('Alerts fetch error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAlerts() }, [])

  const [selectedAlerts, setSelectedAlerts] = useState([])

  // Filter alerts based on selected filter
  const filteredAlerts = alerts.filter((alert) => {
    if (filter === 'all') return true
    if (filter === 'unread') return !alert.read
    return alert.type === filter
  })

  // Count stats
  const unreadCount = alerts.filter((a) => !a.read).length
  const criticalCount = alerts.filter((a) => a.type === 'critical').length
  const warningCount = alerts.filter((a) => a.type === 'warning').length

  // Mark alert as read
  const markAsRead = (alertId) => {
    setAlerts(alerts.map((a) => (a.id === alertId ? { ...a, read: true } : a)))
  }

  // Mark all as read
  const markAllAsRead = () => {
    setAlerts(alerts.map((a) => ({ ...a, read: true })))
  }

  // Delete alert
  const deleteAlert = (alertId) => {
    setAlerts(alerts.filter((a) => a.id !== alertId))
  }

  // Clear all alerts
  const clearAll = () => {
    setAlerts([])
  }

  const filterOptions = [
    { id: 'all', label: 'All', icon: Bell },
    { id: 'unread', label: 'Unread', icon: AlertCircle },
    { id: 'critical', label: 'Critical', icon: AlertTriangle },
    { id: 'warning', label: 'Warning', icon: AlertCircle },
    { id: 'info', label: 'Info', icon: Info },
    { id: 'success', label: 'Resolved', icon: CheckCircle },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spinner size="lg" className="text-accent-green" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Bell className="w-7 h-7 text-accent-green" />
            Alerts & Notifications
          </h1>
          <p className="text-gray-400 mt-1">
            {unreadCount} unread alerts • {criticalCount} critical
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            icon={Check}
            size="sm"
            onClick={markAllAsRead}
            disabled={unreadCount === 0}
          >
            Mark All Read
          </Button>
          <Button
            variant="ghost"
            icon={Trash2}
            size="sm"
            onClick={clearAll}
            disabled={alerts.length === 0}
          >
            Clear All
          </Button>
          <Button variant="outline" icon={Settings} size="sm">
            Settings
          </Button>
          <Button variant="outline" icon={RefreshCw} size="sm" onClick={fetchAlerts}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-4"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-info-blue/20">
              <Bell className="w-5 h-5 text-info-blue" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Total Alerts</p>
              <p className="text-xl font-bold text-white">{alerts.length}</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-4"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning-yellow/20">
              <AlertCircle className="w-5 h-5 text-warning-yellow" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Unread</p>
              <p className="text-xl font-bold text-white">{unreadCount}</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card p-4"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-danger-red/20">
              <AlertTriangle className="w-5 h-5 text-danger-red" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Critical</p>
              <p className="text-xl font-bold text-white">{criticalCount}</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="glass-card p-4"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-orange-500/20">
              <Clock className="w-5 h-5 text-orange-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Warning</p>
              <p className="text-xl font-bold text-white">{warningCount}</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {filterOptions.map((option) => (
          <button
            key={option.id}
            onClick={() => setFilter(option.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap transition-all ${
              filter === option.id
                ? 'bg-accent-green/20 text-accent-green border border-accent-green/50'
                : 'bg-dark-card text-gray-400 border border-dark-border hover:text-white hover:border-gray-500'
            }`}
          >
            <option.icon className="w-4 h-4" />
            <span className="text-sm">{option.label}</span>
            {option.id === 'unread' && unreadCount > 0 && (
              <span className="w-5 h-5 rounded-full bg-danger-red text-white text-xs flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Alerts List */}
      <div className="space-y-3">
        <AnimatePresence mode="popLayout">
          {filteredAlerts.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="glass-card p-12 text-center"
            >
              <div className="w-16 h-16 rounded-full bg-dark-border flex items-center justify-center mx-auto mb-4">
                <Bell className="w-8 h-8 text-gray-500" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">No alerts found</h3>
              <p className="text-gray-400">
                {filter === 'all'
                  ? 'You have no alerts at this time.'
                  : `No ${filter} alerts to display.`}
              </p>
            </motion.div>
          ) : (
            filteredAlerts.map((alert, index) => (
              <motion.div
                key={alert.id}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -100 }}
                transition={{ delay: index * 0.05 }}
              >
                <AlertCard
                  type={alert.type}
                  title={alert.title}
                  message={alert.message}
                  location={alert.location}
                  timestamp={alert.timestamp}
                  read={alert.read}
                  onDismiss={() => deleteAlert(alert.id)}
                />
                
                {/* Quick Actions */}
                {!alert.read && (
                  <div className="flex justify-end mt-2 gap-2">
                    <button
                      onClick={() => markAsRead(alert.id)}
                      className="text-xs text-gray-500 hover:text-accent-green transition-colors"
                    >
                      Mark as read
                    </button>
                  </div>
                )}
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>

      {/* Notification Preferences */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="glass-card p-6"
      >
        <h3 className="text-lg font-semibold text-white mb-4">Notification Preferences</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-center justify-between p-4 bg-dark-bg/50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-danger-red/20">
                <AlertTriangle className="w-5 h-5 text-danger-red" />
              </div>
              <div>
                <p className="text-sm text-white">Critical Alerts</p>
                <p className="text-xs text-gray-500">Super-emitter detections</p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" defaultChecked />
              <div className="w-11 h-6 bg-dark-border rounded-full peer peer-checked:bg-accent-green transition-colors after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
            </label>
          </div>

          <div className="flex items-center justify-between p-4 bg-dark-bg/50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-warning-yellow/20">
                <AlertCircle className="w-5 h-5 text-warning-yellow" />
              </div>
              <div>
                <p className="text-sm text-white">Warning Alerts</p>
                <p className="text-xs text-gray-500">Emission spikes</p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" defaultChecked />
              <div className="w-11 h-6 bg-dark-border rounded-full peer peer-checked:bg-accent-green transition-colors after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
            </label>
          </div>

          <div className="flex items-center justify-between p-4 bg-dark-bg/50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-info-blue/20">
                <Info className="w-5 h-5 text-info-blue" />
              </div>
              <div>
                <p className="text-sm text-white">Info Updates</p>
                <p className="text-xs text-gray-500">Data processing, system updates</p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" />
              <div className="w-11 h-6 bg-dark-border rounded-full peer peer-checked:bg-accent-green transition-colors after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
            </label>
          </div>

          <div className="flex items-center justify-between p-4 bg-dark-bg/50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-accent-green/20">
                <CheckCircle className="w-5 h-5 text-accent-green" />
              </div>
              <div>
                <p className="text-sm text-white">Resolution Updates</p>
                <p className="text-xs text-gray-500">Leak resolution confirmations</p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" defaultChecked />
              <div className="w-11 h-6 bg-dark-border rounded-full peer peer-checked:bg-accent-green transition-colors after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
            </label>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default Alerts
