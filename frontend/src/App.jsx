import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import LiveMap from './pages/LiveMap'
import SuperEmitters from './pages/SuperEmitters'
import Reports from './pages/Reports'
import Alerts from './pages/Alerts'
import DashboardLayout from './components/layout/DashboardLayout'

/**
 * Main App component with routing configuration
 * Routes are split between public landing page and protected dashboard area
 */
function App() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<Landing />} />
      
      {/* Dashboard Routes - wrapped with DashboardLayout */}
      <Route path="/dashboard" element={<DashboardLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="map" element={<LiveMap />} />
        <Route path="super-emitters" element={<SuperEmitters />} />
        <Route path="reports" element={<Reports />} />
        <Route path="alerts" element={<Alerts />} />
      </Route>
    </Routes>
  )
}

export default App
