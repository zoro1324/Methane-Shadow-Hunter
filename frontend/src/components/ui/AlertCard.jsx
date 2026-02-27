import { motion } from 'framer-motion'
import { AlertTriangle, Info, CheckCircle, AlertCircle, X } from 'lucide-react'

/**
 * AlertCard Component
 * Displays notification/alert cards with different severity levels
 */
export const AlertCard = ({ 
  type = 'info', 
  title, 
  message, 
  location, 
  timestamp, 
  onDismiss,
  read = false 
}) => {
  const config = {
    critical: {
      icon: AlertTriangle,
      bgColor: 'bg-danger-red/10',
      borderColor: 'border-danger-red/50',
      iconColor: 'text-danger-red',
      accentColor: 'bg-danger-red',
    },
    warning: {
      icon: AlertCircle,
      bgColor: 'bg-warning-yellow/10',
      borderColor: 'border-warning-yellow/50',
      iconColor: 'text-warning-yellow',
      accentColor: 'bg-warning-yellow',
    },
    info: {
      icon: Info,
      bgColor: 'bg-info-blue/10',
      borderColor: 'border-info-blue/50',
      iconColor: 'text-info-blue',
      accentColor: 'bg-info-blue',
    },
    success: {
      icon: CheckCircle,
      bgColor: 'bg-accent-green/10',
      borderColor: 'border-accent-green/50',
      iconColor: 'text-accent-green',
      accentColor: 'bg-accent-green',
    },
  }

  const { icon: Icon, bgColor, borderColor, iconColor, accentColor } = config[type]

  const formatTimestamp = (ts) => {
    const date = new Date(ts)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className={`relative overflow-hidden rounded-xl border ${borderColor} ${bgColor} ${!read ? 'ring-1 ring-white/10' : 'opacity-75'}`}
    >
      {/* Accent line */}
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${accentColor}`} />
      
      <div className="p-4 pl-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className={`p-2 rounded-lg ${bgColor}`}>
              <Icon className={`w-5 h-5 ${iconColor}`} />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h4 className="font-semibold text-white">{title}</h4>
                {!read && (
                  <span className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
                )}
              </div>
              <p className="text-sm text-gray-400 mt-1">{message}</p>
              {location && (
                <p className="text-xs text-gray-500 mt-2">
                  📍 {location}
                </p>
              )}
              <p className="text-xs text-gray-600 mt-1">
                {formatTimestamp(timestamp)}
              </p>
            </div>
          </div>
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="p-1 hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

/**
 * StatusBadge Component
 * Small badge for showing status in tables and cards
 */
export const StatusBadge = ({ status }) => {
  const config = {
    Active: 'badge-danger',
    Investigating: 'badge-warning',
    Resolved: 'badge-success',
    Scheduled: 'badge-info',
    Critical: 'badge-danger',
    High: 'badge-warning',
    Medium: 'badge-info',
    Low: 'badge-success',
  }

  return (
    <span className={`badge ${config[status] || 'badge-info'}`}>
      {status}
    </span>
  )
}

/**
 * RiskIndicator Component
 * Visual risk level indicator with color coding
 */
export const RiskIndicator = ({ level, showLabel = true }) => {
  const config = {
    Critical: { color: 'bg-danger-red', width: 'w-full' },
    High: { color: 'bg-orange-500', width: 'w-3/4' },
    Medium: { color: 'bg-warning-yellow', width: 'w-1/2' },
    Low: { color: 'bg-accent-green', width: 'w-1/4' },
  }

  const { color, width } = config[level] || config.Medium

  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 bg-dark-border rounded-full overflow-hidden">
        <div className={`h-full ${color} ${width} rounded-full`} />
      </div>
      {showLabel && (
        <span className="text-xs text-gray-400">{level}</span>
      )}
    </div>
  )
}

export default AlertCard
