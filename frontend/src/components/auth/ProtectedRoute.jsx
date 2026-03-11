import { Navigate } from 'react-router-dom'
import { authService } from '../../services/api'

/**
 * ProtectedRoute – Issue #1 fix
 * Checks authentication before rendering children.
 * Redirects to /login if user is not authenticated.
 */
const ProtectedRoute = ({ children }) => {
  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return children
}

export default ProtectedRoute
