import { useState, useEffect, useRef } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  Map,
  AlertTriangle,
  FileText,
  Bell,
  Search,
  User,
  Menu,
  X,
  Satellite,
  ChevronDown,
  Settings,
  LogOut,
} from 'lucide-react'
import { authService, detectedHotspotsService } from '../../services/api'

/**
 * DashboardLayout Component
 * Main layout wrapper for all dashboard pages
 * Includes sidebar navigation and top navbar
 */
const DashboardLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [profileDropdown, setProfileDropdown] = useState(false)
  const [notificationOpen, setNotificationOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()

  // Issue #14: refs for outside-click detection
  const notifRef = useRef(null)
  const profileRef = useRef(null)

  // Issue #11: Live notifications from backend
  const [notifications, setNotifications] = useState([])
  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const hotspots = await detectedHotspotsService.getAll({ ordering: '-anomaly_score', page_size: 5 })
        const list = (Array.isArray(hotspots) ? hotspots : []).slice(0, 5).map((h, i) => ({
          id: h.id || i,
          title: h.severity === 'Critical' ? 'Super-Emitter Detected' :
                 h.severity === 'High' ? 'Emission Spike Alert' :
                 'Hotspot Detected',
          time: h.detected_at ? new Date(h.detected_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Recently',
          type: h.severity === 'Critical' ? 'critical' : h.severity === 'High' ? 'warning' : 'info',
        }))
        setNotifications(list)
      } catch {
        // Gracefully keep empty if API unavailable
      }
    }
    fetchNotifications()
  }, [])

  // Issue #14: Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setNotificationOpen(false)
      }
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setProfileDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Issue #10: Logout handler
  const handleLogout = () => {
    authService.logout()
    navigate('/login')
  }

  // Get stored user info
  const currentUser = authService.getUser()

  // Navigation items configuration
  const navItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Overview', exact: true },
    { path: '/dashboard/map', icon: Map, label: 'Live Map' },
    { path: '/dashboard/super-emitters', icon: AlertTriangle, label: 'Super Emitters' },
    { path: '/dashboard/reports', icon: FileText, label: 'Reports' },
    { path: '/dashboard/alerts', icon: Bell, label: 'Alerts' },
  ]

  return (
    <div className="flex h-screen bg-dark-bg overflow-hidden">
      {/* Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.aside
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="fixed lg:relative z-40 w-64 h-full bg-dark-card border-r border-dark-border flex flex-col"
          >
            {/* Logo Section */}
            <div className="p-6 border-b border-dark-border">
              <Link to="/" className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent-green/20 flex items-center justify-center">
                  <Satellite className="w-6 h-6 text-accent-green" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-white">Methane</h1>
                  <p className="text-xs text-gray-400">Shadow Hunter</p>
                </div>
              </Link>
            </div>

            {/* Navigation Links */}
            <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
              {navItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.exact}
                  className={({ isActive }) =>
                    `sidebar-link ${isActive ? 'active' : ''}`
                  }
                  onClick={() => {
                    // Auto-close sidebar on mobile
                    if (window.innerWidth < 1024) setSidebarOpen(false)
                  }}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </nav>

            {/* System Status */}
            <div className="p-4 border-t border-dark-border">
              <div className="glass-card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
                  <span className="text-xs text-gray-400">System Status</span>
                </div>
                <p className="text-lg font-bold text-white">Online</p>
                <p className="text-xs text-gray-500 mt-1">Last update: 2 min ago</p>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 bg-dark-card border-b border-dark-border flex items-center justify-between px-4 lg:px-6">
          {/* Left Section */}
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-dark-border rounded-lg transition-colors"
            >
              {sidebarOpen ? (
                <X className="w-5 h-5 text-gray-400" />
              ) : (
                <Menu className="w-5 h-5 text-gray-400" />
              )}
            </button>

            {/* Search Bar */}
            <div className="hidden md:flex items-center gap-2 bg-dark-bg border border-dark-border rounded-lg px-4 py-2 w-80">
              <Search className="w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search leaks, locations, reports..."
                className="bg-transparent border-none outline-none text-sm text-gray-300 w-full placeholder-gray-500"
              />
              <span className="text-xs text-gray-600 bg-dark-border px-2 py-0.5 rounded">⌘K</span>
            </div>
          </div>

          {/* Right Section */}
          <div className="flex items-center gap-3">
            {/* Live Status Indicator */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-accent-green/10 rounded-full">
              <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
              <span className="text-xs text-accent-green font-medium">Live</span>
            </div>

            {/* Notifications */}
            <div className="relative" ref={notifRef}>
              <button
                onClick={() => setNotificationOpen(!notificationOpen)}
                className="relative p-2 hover:bg-dark-border rounded-lg transition-colors"
              >
                <Bell className="w-5 h-5 text-gray-400" />
                {notifications.length > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-danger-red text-white text-xs rounded-full flex items-center justify-center">
                    {notifications.length}
                  </span>
                )}
              </button>

              {/* Notifications Dropdown */}
              <AnimatePresence>
                {notificationOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="absolute right-0 mt-2 w-80 glass-card overflow-hidden z-50"
                  >
                    <div className="p-4 border-b border-dark-border">
                      <h3 className="font-semibold text-white">Notifications</h3>
                    </div>
                    <div className="max-h-80 overflow-y-auto">
                      {notifications.length === 0 ? (
                        <div className="p-4 text-center text-gray-500 text-sm">No notifications</div>
                      ) : (
                        notifications.map((notification) => (
                          <div
                            key={notification.id}
                            className="p-4 border-b border-dark-border/50 hover:bg-dark-border/30 cursor-pointer transition-colors"
                          >
                            <div className="flex items-start gap-3">
                              <div
                                className={`w-2 h-2 mt-2 rounded-full ${
                                  notification.type === 'critical'
                                    ? 'bg-danger-red'
                                    : notification.type === 'warning'
                                    ? 'bg-warning-yellow'
                                    : 'bg-info-blue'
                                }`}
                              />
                              <div>
                                <p className="text-sm text-white">{notification.title}</p>
                                <p className="text-xs text-gray-500 mt-1">{notification.time}</p>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                    <div className="p-3 text-center">
                      <Link
                        to="/dashboard/alerts"
                        className="text-sm text-accent-green hover:underline"
                        onClick={() => setNotificationOpen(false)}
                      >
                        View all notifications
                      </Link>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Profile Dropdown */}
            <div className="relative" ref={profileRef}>
              <button
                onClick={() => setProfileDropdown(!profileDropdown)}
                className="flex items-center gap-2 p-1.5 hover:bg-dark-border rounded-lg transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-accent-green/20 flex items-center justify-center">
                  <User className="w-4 h-4 text-accent-green" />
                </div>
                <span className="hidden sm:block text-sm text-gray-300">{currentUser?.username || 'Admin'}</span>
                <ChevronDown className="w-4 h-4 text-gray-500" />
              </button>

              <AnimatePresence>
                {profileDropdown && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="absolute right-0 mt-2 w-48 glass-card overflow-hidden z-50"
                  >
                    <div className="p-2">
                      <button className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-300 hover:bg-dark-border rounded-lg transition-colors">
                        <User className="w-4 h-4" />
                        Profile
                      </button>
                      <button className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-300 hover:bg-dark-border rounded-lg transition-colors">
                        <Settings className="w-4 h-4" />
                        Settings
                      </button>
                      <div className="border-t border-dark-border my-2" />
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-3 px-3 py-2 text-sm text-danger-red hover:bg-dark-border rounded-lg transition-colors"
                      >
                        <LogOut className="w-4 h-4" />
                        Sign Out
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default DashboardLayout
