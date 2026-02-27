import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

/**
 * StatCard Component
 * Displays a single statistic with icon, value, and trend indicator
 * 
 * @param {string} title - Card title
 * @param {string|number} value - Main statistic value
 * @param {string} unit - Unit label (optional)
 * @param {number} change - Percentage change (positive/negative)
 * @param {React.ComponentType} icon - Lucide icon component
 * @param {string} iconColor - Tailwind color class for icon background
 */
const StatCard = ({ 
  title, 
  value, 
  unit = '', 
  change = 0, 
  icon: Icon, 
  iconColor = 'bg-accent-green/20',
  delay = 0 
}) => {
  const getTrendIcon = () => {
    if (change > 0) return <TrendingUp className="w-4 h-4" />
    if (change < 0) return <TrendingDown className="w-4 h-4" />
    return <Minus className="w-4 h-4" />
  }

  const getTrendColor = () => {
    // For emissions/leaks, up is bad (red), down is good (green)
    // Adjust based on context
    if (change > 0) return 'text-danger-red'
    if (change < 0) return 'text-accent-green'
    return 'text-gray-400'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="stat-card group"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-400 mb-1">{title}</p>
          <div className="flex items-baseline gap-2">
            <h3 className="text-3xl font-bold text-white">{value}</h3>
            {unit && <span className="text-sm text-gray-500">{unit}</span>}
          </div>
        </div>
        <div className={`p-3 rounded-xl ${iconColor} group-hover:scale-110 transition-transform duration-300`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>

      {/* Trend Indicator */}
      <div className={`flex items-center gap-1 mt-4 ${getTrendColor()}`}>
        {getTrendIcon()}
        <span className="text-sm font-medium">
          {change > 0 ? '+' : ''}{change}%
        </span>
        <span className="text-xs text-gray-500 ml-1">vs last month</span>
      </div>
    </motion.div>
  )
}

export default StatCard
