import { useState, useEffect, useCallback, createContext, useContext } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, CheckCircle, AlertTriangle, XCircle, Info } from 'lucide-react'

/**
 * Toast notification system
 * Provides context-based toast notifications with auto-dismiss
 */

// ─── Toast Context ──────────────────────────────────────────────────────────
const ToastContext = createContext(null)

let toastIdCounter = 0

const ICONS = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

const COLORS = {
  success: {
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/40',
    icon: 'text-emerald-400',
    bar: 'bg-emerald-500',
  },
  error: {
    bg: 'bg-red-500/10',
    border: 'border-red-500/40',
    icon: 'text-red-400',
    bar: 'bg-red-500',
  },
  warning: {
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/40',
    icon: 'text-yellow-400',
    bar: 'bg-yellow-500',
  },
  info: {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/40',
    icon: 'text-blue-400',
    bar: 'bg-blue-500',
  },
}

// ─── Single Toast Item ──────────────────────────────────────────────────────
const ToastItem = ({ toast, onRemove }) => {
  const Icon = ICONS[toast.type] || Info
  const colors = COLORS[toast.type] || COLORS.info

  useEffect(() => {
    if (toast.duration !== Infinity) {
      const timer = setTimeout(() => onRemove(toast.id), toast.duration || 5000)
      return () => clearTimeout(timer)
    }
  }, [toast, onRemove])

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 80, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      className={`relative overflow-hidden flex items-start gap-3 w-96 p-4 rounded-xl border backdrop-blur-xl shadow-2xl ${colors.bg} ${colors.border}`}
    >
      {/* Progress bar */}
      {toast.duration !== Infinity && (
        <motion.div
          initial={{ scaleX: 1 }}
          animate={{ scaleX: 0 }}
          transition={{ duration: (toast.duration || 5000) / 1000, ease: 'linear' }}
          className={`absolute bottom-0 left-0 right-0 h-0.5 origin-left ${colors.bar}`}
        />
      )}

      <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${colors.icon}`} />

      <div className="flex-1 min-w-0">
        {toast.title && (
          <p className="text-sm font-semibold text-white">{toast.title}</p>
        )}
        <p className="text-sm text-gray-300 leading-relaxed">{toast.message}</p>
      </div>

      <button
        onClick={() => onRemove(toast.id)}
        className="flex-shrink-0 p-1 rounded-lg hover:bg-white/10 transition-colors"
      >
        <X className="w-4 h-4 text-gray-400" />
      </button>
    </motion.div>
  )
}

// ─── Toast Provider ─────────────────────────────────────────────────────────
export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([])

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback(({ type = 'info', title, message, duration = 5000 }) => {
    const id = ++toastIdCounter
    setToasts((prev) => [...prev, { id, type, title, message, duration }])
    return id
  }, [])

  const toast = {
    success: (message, title = 'Success') => addToast({ type: 'success', title, message }),
    error: (message, title = 'Error') => addToast({ type: 'error', title, message }),
    warning: (message, title = 'Warning') => addToast({ type: 'warning', title, message }),
    info: (message, title = 'Info') => addToast({ type: 'info', title, message }),
  }

  return (
    <ToastContext.Provider value={toast}>
      {children}

      {/* Toast container - fixed top-right */}
      <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-3">
        <AnimatePresence mode="popLayout">
          {toasts.map((t) => (
            <ToastItem key={t.id} toast={t} onRemove={removeToast} />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

// ─── Hook ───────────────────────────────────────────────────────────────────
export const useToast = () => {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within <ToastProvider>')
  return ctx
}
