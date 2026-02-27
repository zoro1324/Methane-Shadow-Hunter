import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Eye, EyeOff, UserPlus, Flame, ArrowLeft, Loader2, Check } from 'lucide-react'
import { authService } from '../services/api'
import { useToast } from '../components/ui/Toast'

/**
 * Signup Page Component
 * Full registration form with inline field validation and toast notifications
 */
const Signup = () => {
  const navigate = useNavigate()
  const toast = useToast()

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    username: '',
    email: '',
    password: '',
    confirm_password: '',
  })
  const [errors, setErrors] = useState({})
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)

  // ─── Password strength checker ────────────────────────────────────────
  const getPasswordStrength = (pw) => {
    if (!pw) return { score: 0, label: '', color: '' }
    let score = 0
    if (pw.length >= 8) score++
    if (/[A-Z]/.test(pw)) score++
    if (/[0-9]/.test(pw)) score++
    if (/[^A-Za-z0-9]/.test(pw)) score++

    const levels = [
      { label: 'Weak', color: 'bg-red-500' },
      { label: 'Fair', color: 'bg-yellow-500' },
      { label: 'Good', color: 'bg-blue-500' },
      { label: 'Strong', color: 'bg-emerald-500' },
    ]
    return { score, ...levels[Math.min(score, levels.length) - 1] || levels[0] }
  }

  const pwStrength = getPasswordStrength(form.password)

  // ─── Client-side validation ───────────────────────────────────────────
  const validate = () => {
    const errs = {}
    if (!form.username.trim()) errs.username = 'Username is required.'
    else if (form.username.trim().length < 3) errs.username = 'Username must be at least 3 characters.'
    if (!form.email.trim()) errs.email = 'Email is required.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) errs.email = 'Enter a valid email address.'
    if (!form.password) errs.password = 'Password is required.'
    else if (form.password.length < 8) errs.password = 'Password must be at least 8 characters.'
    if (!form.confirm_password) errs.confirm_password = 'Please confirm your password.'
    else if (form.password !== form.confirm_password) errs.confirm_password = 'Passwords do not match.'
    return errs
  }

  // ─── Handle input change ─────────────────────────────────────────────
  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }))
  }

  // ─── Submit ──────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault()
    const clientErrors = validate()
    if (Object.keys(clientErrors).length) {
      setErrors(clientErrors)
      toast.warning('Please fix the highlighted fields.', 'Validation Error')
      return
    }

    setLoading(true)
    setErrors({})

    try {
      const data = await authService.register({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        confirm_password: form.confirm_password,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
      })
      authService.saveAuth(data)
      toast.success('Your account has been created. Welcome aboard!', 'Registration Successful')
      navigate('/dashboard')
    } catch (err) {
      const resp = err.response?.data
      if (resp?.errors) {
        const fieldErrors = {}
        Object.entries(resp.errors).forEach(([key, val]) => {
          const msg = Array.isArray(val) ? val[0] : val
          if (key === 'non_field_errors') {
            toast.error(msg, 'Registration Failed')
          } else {
            fieldErrors[key] = msg
            // Show toast for important errors
            if (key === 'username') toast.error(msg, 'Username Taken')
            if (key === 'email') toast.error(msg, 'Email Already Exists')
          }
        })
        setErrors(fieldErrors)
      } else {
        toast.error('Something went wrong. Please try again.', 'Registration Failed')
      }
    } finally {
      setLoading(false)
    }
  }

  // ─── Reusable field error ─────────────────────────────────────────────
  const FieldError = ({ msg }) =>
    msg ? (
      <motion.p
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-1.5 text-xs text-red-400 flex items-center gap-1"
      >
        <span className="inline-block w-1 h-1 rounded-full bg-red-400" />
        {msg}
      </motion.p>
    ) : null

  const inputCls = (field) =>
    `w-full px-4 py-3 bg-dark-bg border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 transition-all ${
      errors[field]
        ? 'border-red-500 focus:ring-red-500/40'
        : 'border-dark-border focus:ring-accent-green/40 focus:border-accent-green'
    }`

  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center relative overflow-hidden py-8">
      {/* Background effects */}
      <div className="fixed inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-dark-bg via-dark-bg to-emerald-950/20" />
        <motion.div
          animate={{ scale: [1, 1.2, 1], opacity: [0.2, 0.4, 0.2] }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute top-1/4 right-1/4 w-96 h-96 bg-accent-green/10 rounded-full blur-3xl"
        />
        <motion.div
          animate={{ scale: [1.2, 1, 1.2], opacity: [0.15, 0.3, 0.15] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute bottom-1/3 left-1/4 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl"
        />
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(rgba(34, 197, 94, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(34, 197, 94, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px',
          }}
        />
      </div>

      {/* Back to home */}
      <Link
        to="/"
        className="absolute top-6 left-6 z-20 flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span className="text-sm">Back to Home</span>
      </Link>

      {/* Card */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 w-full max-w-lg mx-4"
      >
        <div className="glass-card p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <Link to="/" className="inline-flex items-center gap-3 mb-6">
              <div className="w-12 h-12 rounded-xl bg-accent-green/20 flex items-center justify-center glow-green">
                <Flame className="w-7 h-7 text-accent-green" />
              </div>
            </Link>
            <h1 className="text-2xl font-bold text-white mb-2">Create Account</h1>
            <p className="text-gray-400 text-sm">Join Methane Shadow Hunter and start monitoring</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {/* Name row */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="first_name" className="block text-sm font-medium text-gray-300 mb-1.5">
                  First Name
                </label>
                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  autoComplete="given-name"
                  value={form.first_name}
                  onChange={handleChange}
                  placeholder="John"
                  className={inputCls('first_name')}
                />
                <FieldError msg={errors.first_name} />
              </div>
              <div>
                <label htmlFor="last_name" className="block text-sm font-medium text-gray-300 mb-1.5">
                  Last Name
                </label>
                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  autoComplete="family-name"
                  value={form.last_name}
                  onChange={handleChange}
                  placeholder="Doe"
                  className={inputCls('last_name')}
                />
                <FieldError msg={errors.last_name} />
              </div>
            </div>

            {/* Username */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-1.5">
                Username <span className="text-red-400">*</span>
              </label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                value={form.username}
                onChange={handleChange}
                placeholder="johndoe"
                className={inputCls('username')}
              />
              <FieldError msg={errors.username} />
            </div>

            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1.5">
                Email <span className="text-red-400">*</span>
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={handleChange}
                placeholder="john@example.com"
                className={inputCls('email')}
              />
              <FieldError msg={errors.email} />
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1.5">
                Password <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={form.password}
                  onChange={handleChange}
                  placeholder="Min 8 characters"
                  className={`${inputCls('password')} pr-12`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {/* Strength meter */}
              {form.password && (
                <div className="mt-2">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4].map((i) => (
                      <div
                        key={i}
                        className={`h-1 flex-1 rounded-full transition-colors ${
                          i <= pwStrength.score ? pwStrength.color : 'bg-dark-border'
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Strength: <span className="text-gray-300">{pwStrength.label}</span>
                  </p>
                </div>
              )}
              <FieldError msg={errors.password} />
            </div>

            {/* Confirm Password */}
            <div>
              <label htmlFor="confirm_password" className="block text-sm font-medium text-gray-300 mb-1.5">
                Confirm Password <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <input
                  id="confirm_password"
                  name="confirm_password"
                  type={showConfirm ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={form.confirm_password}
                  onChange={handleChange}
                  placeholder="Re-enter password"
                  className={`${inputCls('confirm_password')} pr-12`}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                >
                  {showConfirm ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {/* Match indicator */}
              {form.confirm_password && form.password === form.confirm_password && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="mt-1.5 text-xs text-emerald-400 flex items-center gap-1"
                >
                  <Check className="w-3 h-3" />
                  Passwords match
                </motion.p>
              )}
              <FieldError msg={errors.confirm_password} />
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary flex items-center justify-center gap-2 py-3 mt-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <UserPlus className="w-5 h-5" />
              )}
              {loading ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-4 my-6">
            <div className="flex-1 h-px bg-dark-border" />
            <span className="text-xs text-gray-500">OR</span>
            <div className="flex-1 h-px bg-dark-border" />
          </div>

          {/* Login link */}
          <p className="text-center text-sm text-gray-400">
            Already have an account?{' '}
            <Link to="/login" className="text-accent-green hover:text-accent-green-dark font-medium transition-colors">
              Sign In
            </Link>
          </p>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-gray-600 mt-6">
          By creating an account, you agree to our Terms of Service and Privacy Policy.
        </p>
      </motion.div>
    </div>
  )
}

export default Signup
