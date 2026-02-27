import { motion } from 'framer-motion'

/**
 * Button Component
 * Reusable button with multiple variants
 */
export const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  icon: Icon,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  className = '',
  ...props
}) => {
  const variants = {
    primary: 'bg-accent-green hover:bg-accent-green-dark text-white shadow-lg hover:shadow-accent-green/25',
    secondary: 'bg-transparent border-2 border-accent-green text-accent-green hover:bg-accent-green hover:text-white',
    danger: 'bg-danger-red hover:bg-red-600 text-white shadow-lg hover:shadow-danger-red/25',
    ghost: 'bg-transparent hover:bg-dark-border text-gray-400 hover:text-white',
    outline: 'bg-transparent border border-dark-border text-gray-400 hover:text-white hover:border-accent-green',
  }

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-5 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
    xl: 'px-8 py-4 text-lg',
  }

  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      className={`
        inline-flex items-center justify-center gap-2 
        font-semibold rounded-lg transition-all duration-300
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]}
        ${sizes[size]}
        ${className}
      `}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : (
        <>
          {Icon && iconPosition === 'left' && <Icon className="w-4 h-4" />}
          {children}
          {Icon && iconPosition === 'right' && <Icon className="w-4 h-4" />}
        </>
      )}
    </motion.button>
  )
}

/**
 * GlassCard Component
 * Card with glassmorphism effect
 */
export const GlassCard = ({ 
  children, 
  className = '', 
  hover = true,
  padding = 'p-6',
  ...props 
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        glass-card ${padding}
        ${hover ? 'hover:border-accent-green/50 transition-all duration-300' : ''}
        ${className}
      `}
      {...props}
    >
      {children}
    </motion.div>
  )
}

/**
 * Loading Spinner Component
 */
export const Spinner = ({ size = 'md', className = '' }) => {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
  }

  return (
    <svg
      className={`animate-spin ${sizes[size]} ${className}`}
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
        fill="none"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

/**
 * Section Header Component
 */
export const SectionHeader = ({ 
  title, 
  subtitle, 
  action,
  className = '' 
}) => {
  return (
    <div className={`flex items-center justify-between mb-6 ${className}`}>
      <div>
        <h2 className="text-xl font-bold text-white">{title}</h2>
        {subtitle && (
          <p className="text-sm text-gray-400 mt-1">{subtitle}</p>
        )}
      </div>
      {action && action}
    </div>
  )
}

/**
 * Empty State Component
 */
export const EmptyState = ({ 
  icon: Icon, 
  title, 
  description, 
  action 
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {Icon && (
        <div className="w-16 h-16 rounded-full bg-dark-border flex items-center justify-center mb-4">
          <Icon className="w-8 h-8 text-gray-500" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-gray-400 max-w-md mb-4">{description}</p>
      )}
      {action && action}
    </div>
  )
}

export default {
  Button,
  GlassCard,
  Spinner,
  SectionHeader,
  EmptyState,
}
