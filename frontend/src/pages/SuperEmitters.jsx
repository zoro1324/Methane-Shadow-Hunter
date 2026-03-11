import { useState, useEffect, useMemo, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  AlertTriangle, Eye, MapPin, Search, Building2,
  TrendingUp, Activity, Zap, Satellite, Calendar, Radius,
} from 'lucide-react'
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { MapContainer, TileLayer, CircleMarker, Circle, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import DataTable from '../components/tables/DataTable'
import { StatusBadge } from '../components/ui/AlertCard'
import { Spinner } from '../components/ui/Common'
import { facilitiesService, geeService } from '../services/api'

// ── Fix default Leaflet marker icon ──────────────────────────────────────────
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl:       'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl:     'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

// ── Date helpers ─────────────────────────────────────────────────────────────
const toDateStr = (d) => d.toISOString().split('T')[0]
const _today    = new Date()
const _30ago    = new Date(_today); _30ago.setDate(_today.getDate() - 30)

// ── Colour palette ───────────────────────────────────────────────────────────
const SEV_COLOR = { Severe: '#ef4444', Moderate: '#f59e0b', Low: '#22c55e' }
const PRI_LABEL = { 1: 'Critical', 2: 'High', 3: 'Moderate' }
const PRI_COLOR = { 1: '#ef4444', 2: '#f59e0b', 3: '#22c55e' }

// ── Custom recharts tooltip ──────────────────────────────────────────────────
const DarkTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-dark-card border border-dark-border rounded-lg p-3 shadow-xl text-xs">
      {label && <p className="text-gray-400 mb-1 font-medium">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color || p.fill }} className="font-semibold">
          {p.name}: {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}
        </p>
      ))}
    </div>
  )
}

// ── Layout helpers ───────────────────────────────────────────────────────────
const Card = ({ children, className = '' }) => (
  <div className={`glass-card p-5 ${className}`}>{children}</div>
)
const CardTitle = ({ children }) => (
  <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">{children}</h3>
)

// ── Sigma-score histogram builder ────────────────────────────────────────────
const buildSigmaHistogram = (hotspots) => {
  const bins = [
    { range: '0.5–1.0', min: 0.5, max: 1.0,     count: 0, fill: '#22c55e' },
    { range: '1.0–1.5', min: 1.0, max: 1.5,     count: 0, fill: '#22c55e' },
    { range: '1.5–2.0', min: 1.5, max: 2.0,     count: 0, fill: '#f59e0b' },
    { range: '2.0–3.0', min: 2.0, max: 3.0,     count: 0, fill: '#f59e0b' },
    { range: '3.0+',    min: 3.0, max: Infinity, count: 0, fill: '#ef4444' },
  ]
  for (const h of hotspots) {
    for (const b of bins) {
      if (h.score >= b.min && h.score < b.max) { b.count++; break }
    }
  }
  return bins.filter(b => b.count > 0)
}

// Simple way: use MapContainer key to re-mount when center changes
// (more reliable than imperative setView across re-renders)

/* ═══════════════════════════════════════════════════════════════════════════════
   SUPER EMITTERS — Company-Centric CH4 Analysis
   ═══════════════════════════════════════════════════════════════════════════════ */
const SuperEmitters = () => {
  // ── Facility search state ─────────────────────────────────────────────────
  const [query, setQuery]                     = useState('')
  const [facilities, setFacilities]           = useState([])
  const [showDropdown, setShowDropdown]       = useState(false)
  const [selectedFacility, setSelectedFacility] = useState(null)
  const searchRef = useRef(null)

  // ── Query params ──────────────────────────────────────────────────────────
  const [fromDate, setFromDate]               = useState(toDateStr(_30ago))
  const [toDate, setToDate]                   = useState(toDateStr(_today))
  const [radiusKm, setRadiusKm]              = useState(50)

  // ── Analysis result state ─────────────────────────────────────────────────
  const [hotspots, setHotspots]               = useState([])
  const [stats, setStats]                     = useState(null)
  const [tileDateRange, setTileDateRange]     = useState(null)
  const [todayTile, setTodayTile]             = useState(null)
  const [histTile, setHistTile]               = useState(null)
  const [center, setCenter]                   = useState(null)  // { lat, lng, radius_km }
  const [facilityInfo, setFacilityInfo]       = useState(null)

  // ── UI state ──────────────────────────────────────────────────────────────
  const [loading, setLoading]                 = useState(false)
  const [error, setError]                     = useState(null)
  const [selectedEmitter, setSelectedEmitter] = useState(null)
  const [activeFilter, setActiveFilter]       = useState('All')
  const [analysisRun, setAnalysisRun]         = useState(false)

  // ── Search facilities on query change ─────────────────────────────────────
  useEffect(() => {
    if (query.length < 2) { setFacilities([]); return }
    const timer = setTimeout(async () => {
      try {
        const results = await facilitiesService.search(query)
        setFacilities(Array.isArray(results) ? results : [])
      } catch { setFacilities([]) }
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  // ── Close dropdown on outside click ───────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) setShowDropdown(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // ── Select facility from dropdown ─────────────────────────────────────────
  const pickFacility = (fac) => {
    setSelectedFacility(fac)
    setQuery(fac.name)
    setShowDropdown(false)
  }

  // ── Run company analysis ──────────────────────────────────────────────────
  const runAnalysis = async () => {
    if (!selectedFacility) return
    setLoading(true); setError(null); setAnalysisRun(false)
    try {
      const result = await geeService.getCompanyAnalysis({
        facilityId: selectedFacility.id,
        radiusKm,
        startDate: fromDate,
        endDate:   toDate,
      })
      const hs = Array.isArray(result.hotspots) ? result.hotspots : []
      setHotspots(hs.map(h => ({
        id:         h.id,
        location:   `${h.id}`,
        lat:        h.latitude,
        lng:        h.longitude,
        ch4:        h.ch4_ppb,
        score:      h.anomaly_score,
        severity:   h.severity,
        priority:   h.priority,
        status:     h.priority === 1 ? 'Active' : h.priority === 2 ? 'Investigating' : 'Resolved',
        detectedAt: `${h.detected_at}T00:00:00Z`,
        distanceKm: h.distance_km ?? null,
        source:     'gee',
      })))
      setStats(result.stats    || null)
      setHistTile(result.tile_url   || null)
      setTodayTile(result.today_tile || null)
      setCenter(result.center       || null)
      setFacilityInfo(result.facility || null)
      setTileDateRange({ from: result.start_date, to: result.end_date })
      setAnalysisRun(true)
    } catch (err) {
      console.error(err)
      const msg = err?.response?.data?.detail || err?.response?.data?.error || err.message
      setError(`Analysis unavailable. Please try again or check your connection.`)
    } finally {
      setLoading(false)
    }
  }

  // ── Derived / memoised chart data ─────────────────────────────────────────
  const filtered = useMemo(() =>
    activeFilter === 'All' ? hotspots : hotspots.filter(h => h.severity === activeFilter),
    [hotspots, activeFilter]
  )

  const histData = useMemo(() => buildSigmaHistogram(hotspots), [hotspots])

  const severityData = useMemo(() => {
    const c = { Severe: 0, Moderate: 0, Low: 0 }
    hotspots.forEach(h => { c[h.severity] = (c[h.severity] || 0) + 1 })
    return Object.entries(c).map(([name, value]) => ({ name, value })).filter(d => d.value > 0)
  }, [hotspots])

  const top10 = useMemo(() =>
    [...hotspots].sort((a, b) => b.ch4 - a.ch4).slice(0, 10).map(h => ({
      name: h.id.replace('GEE-', '#'),
      ch4:  h.ch4,
      fill: SEV_COLOR[h.severity] || '#22c55e',
    })),
    [hotspots]
  )

  const mapCenter = useMemo(() => {
    if (center) return [center.lat, center.lng]
    if (selectedFacility) return [parseFloat(selectedFacility.latitude), parseFloat(selectedFacility.longitude)]
    return [20.5, 78.9]
  }, [center, selectedFacility])

  const mapZoom = useMemo(() => {
    if (!radiusKm) return 8
    if (radiusKm <= 20)  return 10
    if (radiusKm <= 50)  return 9
    if (radiusKm <= 100) return 8
    return 7
  }, [radiusKm])

  const critCount = hotspots.filter(h => h.priority === 1).length
  const highCount = hotspots.filter(h => h.priority === 2).length
  const avgScore  = hotspots.length
    ? (hotspots.reduce((s, h) => s + h.score, 0) / hotspots.length).toFixed(2)
    : 0
  const maxCH4 = hotspots.length ? Math.max(...hotspots.map(h => h.ch4)) : 0

  // ── Table columns ─────────────────────────────────────────────────────────
  const columns = [
    {
      key: 'id', label: 'ID', sortable: true,
      render: v => <span className="font-mono text-accent-green text-xs">{v}</span>,
    },
    {
      key: 'location', label: 'Location', sortable: true,
      render: (v, row) => (
        <div className="flex items-center gap-2">
          <MapPin className="w-3.5 h-3.5 text-gray-500 shrink-0" />
          <div>
            <p className="text-white text-sm font-medium">{v}</p>
            <p className="text-xs text-gray-500">{row.lat.toFixed(4)}°N, {row.lng.toFixed(4)}°E</p>
          </div>
        </div>
      ),
    },
    {
      key: 'ch4', label: 'CH₄ (ppb)', sortable: true,
      render: (v, row) => (
        <div className="flex items-center gap-2">
          <div className="w-20 h-1.5 bg-dark-border rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all"
              style={{ width: `${Math.min(100, (v / (maxCH4 || 1)) * 100)}%`, background: SEV_COLOR[row.severity] }} />
          </div>
          <span className="text-white font-semibold text-sm">{v.toFixed(1)}</span>
        </div>
      ),
    },
    {
      key: 'score', label: 'Anomaly σ', sortable: true,
      render: v => (
        <span className={`font-mono text-sm font-bold ${
          v > 3 ? 'text-danger-red' : v > 2 ? 'text-warning-yellow' : 'text-accent-green'
        }`}>{v.toFixed(3)}</span>
      ),
    },
    {
      key: 'severity', label: 'Severity', sortable: true,
      render: v => (
        <span className="px-2 py-0.5 rounded-full text-xs font-semibold"
          style={{ background: `${SEV_COLOR[v]}22`, color: SEV_COLOR[v] }}>{v}</span>
      ),
    },
    {
      key: 'distanceKm', label: 'Distance', sortable: true,
      render: v => <span className="text-gray-400 text-xs">{v != null ? `${v} km` : '—'}</span>,
    },
    {
      key: 'actions', label: '',
      render: (_, row) => (
        <button onClick={e => { e.stopPropagation(); setSelectedEmitter(row) }}
          className="p-1.5 hover:bg-dark-border rounded-lg transition-colors">
          <Eye className="w-4 h-4 text-gray-400 hover:text-accent-green" />
        </button>
      ),
    },
  ]

  /* ═══════════════════════════════════════════════════════════════════════════
     RENDER
     ═══════════════════════════════════════════════════════════════════════════ */
  return (
    <div className="space-y-6">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Building2 className="w-7 h-7 text-info-blue" />
          Company CH₄ Analysis
        </h1>
        <p className="text-gray-400 mt-1">
          Search a facility, set the date range &amp; radius, and analyse Sentinel-5P TROPOMI CH₄ data around it.
        </p>
      </div>

      {/* ── Query Panel ─────────────────────────────────────────────────────── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        className="glass-card p-5 border border-dark-border space-y-4">

        {/* Row 1 — Company search */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1" ref={searchRef}>
            <div className="flex items-center gap-2 bg-dark-bg border border-dark-border rounded-lg px-3 py-2 focus-within:border-accent-green transition-colors">
              <Search className="w-4 h-4 text-gray-500 shrink-0" />
              <input
                type="text"
                value={query}
                onChange={e => { setQuery(e.target.value); setShowDropdown(true); setSelectedFacility(null) }}
                onFocus={() => setShowDropdown(true)}
                placeholder="Search company / facility name…"
                className="bg-transparent text-white text-sm flex-1 outline-none placeholder:text-gray-600"
              />
              {selectedFacility && (
                <span className="px-2 py-0.5 rounded-full text-xs bg-accent-green/20 text-accent-green font-semibold shrink-0">
                  Selected
                </span>
              )}
            </div>

            {/* Dropdown */}
            <AnimatePresence>
              {showDropdown && facilities.length > 0 && (
                <motion.ul
                  initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
                  className="absolute z-50 top-full mt-1 w-full max-h-64 overflow-auto bg-dark-card border border-dark-border rounded-xl shadow-xl">
                  {facilities.map(f => (
                    <li key={f.id}
                      onClick={() => pickFacility(f)}
                      className="flex items-start gap-3 px-4 py-3 hover:bg-dark-border/60 cursor-pointer transition-colors border-b border-dark-border/40 last:border-0">
                      <Building2 className="w-4 h-4 text-info-blue mt-0.5 shrink-0" />
                      <div className="min-w-0">
                        <p className="text-white text-sm font-medium truncate">{f.name}</p>
                        <p className="text-xs text-gray-500 truncate">
                          {f.operator} · {f.type} · {f.state}
                        </p>
                        <p className="text-xs text-gray-600">
                          {parseFloat(f.latitude).toFixed(4)}°N, {parseFloat(f.longitude).toFixed(4)}°E
                        </p>
                      </div>
                    </li>
                  ))}
                </motion.ul>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Row 2 — Date range, radius, action */}
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5 text-gray-500" />
            <div>
              <label className="text-xs text-gray-500 block mb-1">From</label>
              <input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)}
                className="bg-dark-bg border border-dark-border text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-accent-green transition-colors" />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div>
              <label className="text-xs text-gray-500 block mb-1">To</label>
              <input type="date" value={toDate} onChange={e => setToDate(e.target.value)}
                className="bg-dark-bg border border-dark-border text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-accent-green transition-colors" />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Radius className="w-3.5 h-3.5 text-gray-500" />
            <div>
              <label className="text-xs text-gray-500 block mb-1">Radius (km)</label>
              <select value={radiusKm} onChange={e => setRadiusKm(Number(e.target.value))}
                className="bg-dark-bg border border-dark-border text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-accent-green transition-colors">
                {[10, 20, 30, 50, 75, 100, 150, 200].map(r => (
                  <option key={r} value={r}>{r} km</option>
                ))}
              </select>
            </div>
          </div>
          <button
            onClick={runAnalysis}
            disabled={!selectedFacility || loading}
            className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold bg-info-blue hover:bg-blue-500 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed ml-auto">
            {loading
              ? <><Spinner size="sm" className="w-4 h-4" /> Analysing…</>
              : <><Satellite className="w-4 h-4" /> Analyse with Earth Engine</>}
          </button>
        </div>

        {/* Selected facility chip */}
        {selectedFacility && (
          <div className="flex flex-wrap items-center gap-3 p-3 rounded-xl bg-dark-bg border border-dark-border/60 text-xs">
            <Building2 className="w-4 h-4 text-info-blue shrink-0" />
            <span className="text-white font-semibold">{selectedFacility.name}</span>
            <span className="text-gray-500">|</span>
            <span className="text-gray-400">{selectedFacility.operator}</span>
            <span className="text-gray-500">|</span>
            <span className="px-2 py-0.5 rounded-full bg-info-blue/20 text-info-blue font-medium">{selectedFacility.type}</span>
            <span className="text-gray-500">|</span>
            <span className="text-gray-400">{selectedFacility.state}</span>
            <span className="text-gray-500">|</span>
            <span className="text-gray-400 font-mono">
              {parseFloat(selectedFacility.latitude).toFixed(4)}°N, {parseFloat(selectedFacility.longitude).toFixed(4)}°E
            </span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-3 rounded-lg bg-danger-red/10 border border-danger-red/30">
            <p className="text-danger-red text-xs">{error}</p>
          </div>
        )}
      </motion.div>

      {/* ── Stats banner (shown after analysis) ────────────────────────────── */}
      <AnimatePresence>
        {analysisRun && stats && (
          <motion.div
            initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="flex flex-wrap items-center gap-x-6 gap-y-2 p-3 rounded-xl border border-info-blue/40 bg-info-blue/10 text-xs">
            <span className="flex items-center gap-1.5 text-info-blue font-semibold">
              <Satellite className="w-3.5 h-3.5" />
              Satellite Analysis Complete
            </span>
            <span className="text-gray-400">
              Facility: <strong className="text-white">{facilityInfo?.name || '—'}</strong>
            </span>
            <span className="text-gray-400">
              Period: <strong className="text-white">{fromDate}</strong> → <strong className="text-white">{toDate}</strong>
            </span>
            <span className="text-gray-400">
              Radius: <strong className="text-white">{radiusKm} km</strong>
            </span>
            <span className="text-gray-400">
              Sampled: <strong className="text-white">{stats.total_sampled?.toLocaleString()}</strong> pts
            </span>
            <span className="text-gray-400">
              Mean CH₄: <strong className="text-white">{stats.mean} ppb</strong>
            </span>
            <span className="text-gray-400">
              σ: <strong className="text-white">{stats.std} ppb</strong>
            </span>
            <span className="ml-auto text-accent-green font-semibold">
              {stats.count} anomalous hotspot{stats.count !== 1 ? 's' : ''} detected
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Content area: only shown after first successful analysis ──────── */}
      {analysisRun && (
        <>
          {/* ── Filter bar ─────────────────────────────────────────────────── */}
          <div className="flex items-center gap-2 flex-wrap">
            {['All', 'Severe', 'Moderate', 'Low'].map(f => (
              <button key={f} onClick={() => setActiveFilter(f)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  activeFilter === f
                    ? f === 'Severe'   ? 'bg-danger-red text-white'
                    : f === 'Moderate' ? 'bg-warning-yellow text-black'
                    : f === 'Low'      ? 'bg-accent-green text-black'
                    :                    'bg-accent-green text-black'
                    : 'bg-dark-border text-gray-400 hover:text-white'
                }`}>{f}
              </button>
            ))}
          </div>

          {/* ── KPI strip ──────────────────────────────────────────────────── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Total Detected',  value: hotspots.length,      color: 'text-white',          icon: Activity,      bg: 'bg-info-blue/20',      ic: 'text-info-blue' },
              { label: 'Critical (P1)',   value: critCount,            color: 'text-danger-red',     icon: AlertTriangle, bg: 'bg-danger-red/20',     ic: 'text-danger-red' },
              { label: 'High (P2)',       value: highCount,            color: 'text-warning-yellow', icon: Zap,           bg: 'bg-warning-yellow/20', ic: 'text-warning-yellow' },
              { label: 'Mean CH₄ (ppb)',  value: stats?.mean ?? '—',   color: 'text-info-blue',      icon: Satellite,     bg: 'bg-info-blue/20',      ic: 'text-info-blue' },
            ].map(({ label, value, color, icon: Icon, bg, ic }, i) => (
              <motion.div key={label}
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}
                className="glass-card p-4 flex items-center gap-4">
                <div className={`p-3 rounded-xl shrink-0 ${bg}`}><Icon className={`w-5 h-5 ${ic}`} /></div>
                <div>
                  <p className="text-xs text-gray-400">{label}</p>
                  <p className={`text-2xl font-bold ${color}`}>{value}</p>
                </div>
              </motion.div>
            ))}
          </div>

          {/* ── Chart row: Sigma histogram (2/3) + Severity donut (1/3) ──── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
              className="lg:col-span-2">
              <Card>
                <CardTitle>Anomaly σ Distribution — {fromDate} to {toDate}</CardTitle>
                {histData.length === 0 ? (
                  <div className="h-52 flex flex-col items-center justify-center gap-2 text-gray-500">
                    <TrendingUp className="w-8 h-8 opacity-30" />
                    <p className="text-sm">No anomalous concentrations found for this period</p>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={histData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="range" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false}
                        label={{ value: 'z-score (σ)', position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                      <Tooltip content={<DarkTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                      <Bar dataKey="count" name="Hotspot count" radius={[4, 4, 0, 0]}>
                        {histData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
              <Card className="flex flex-col">
                <CardTitle>Severity Distribution</CardTitle>
                {severityData.length === 0 ? (
                  <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">No data</div>
                ) : (
                  <>
                    <ResponsiveContainer width="100%" height={180}>
                      <PieChart>
                        <Pie data={severityData} cx="50%" cy="50%"
                          innerRadius={52} outerRadius={78} paddingAngle={3} dataKey="value" strokeWidth={0}>
                          {severityData.map(entry => (
                            <Cell key={entry.name} fill={SEV_COLOR[entry.name] || '#6b7280'} />
                          ))}
                        </Pie>
                        <Tooltip content={<DarkTooltip />} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="flex flex-col gap-2 mt-2">
                      {severityData.map(d => (
                        <div key={d.name} className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full shrink-0"
                              style={{ background: SEV_COLOR[d.name], display: 'inline-block' }} />
                            <span className="text-gray-400">{d.name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1 bg-dark-border rounded-full overflow-hidden">
                              <div className="h-full rounded-full" style={{
                                width: `${(d.value / hotspots.length) * 100}%`,
                                background: SEV_COLOR[d.name],
                              }} />
                            </div>
                            <span className="font-semibold w-6 text-right" style={{ color: SEV_COLOR[d.name] }}>{d.value}</span>
                          </div>
                        </div>
                      ))}
                      <div className="flex items-center justify-between text-xs border-t border-dark-border pt-2 mt-1">
                        <span className="text-gray-500">Avg anomaly σ</span>
                        <span className="text-white font-bold">{avgScore}</span>
                      </div>
                    </div>
                  </>
                )}
              </Card>
            </motion.div>
          </div>

          {/* ── Spatial map (Today snapshot) + Top-10 bar ───────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card>
                <CardTitle>
                  {facilityInfo?.name || 'Facility'} — Live CH₄ Snapshot (last 7 days)
                </CardTitle>
                <div className="rounded-xl overflow-hidden border border-dark-border" style={{ height: 340 }}>
                  <MapContainer
                    key={`${mapCenter[0]}-${mapCenter[1]}-${radiusKm}`}
                    center={mapCenter} zoom={mapZoom}
                    style={{ height: '100%', width: '100%' }}
                    scrollWheelZoom zoomControl attributionControl={false}>
                    <TileLayer
                      url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                      attribution="© CartoDB"
                    />
                    {/* Today CH₄ tile overlay */}
                    {todayTile && (
                      <TileLayer url={todayTile} opacity={0.6} attribution="Copernicus Sentinel-5P" />
                    )}
                    {/* Search radius circle */}
                    {center && (
                      <Circle
                        center={[center.lat, center.lng]}
                        radius={center.radius_km * 1000}
                        pathOptions={{ color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.06, weight: 1.5, dashArray: '6 4' }}
                      />
                    )}
                    {/* Facility marker */}
                    {center && (
                      <Marker position={[center.lat, center.lng]}>
                        <Popup>
                          <div style={{ fontSize: 12, lineHeight: 1.6 }}>
                            <strong>{facilityInfo?.name || 'Facility'}</strong><br />
                            {facilityInfo?.operator}<br />
                            Type: {facilityInfo?.type}<br />
                            {center.lat.toFixed(4)}°N, {center.lng.toFixed(4)}°E
                          </div>
                        </Popup>
                      </Marker>
                    )}
                    {/* Anomaly hotspots */}
                    {filtered.map(h => (
                      <CircleMarker key={h.id}
                        center={[h.lat, h.lng]}
                        radius={h.priority === 1 ? 10 : h.priority === 2 ? 7 : 5}
                        pathOptions={{
                          color:       SEV_COLOR[h.severity],
                          fillColor:   SEV_COLOR[h.severity],
                          fillOpacity: 0.8,
                          weight:      h.priority === 1 ? 2.5 : 1,
                        }}>
                        <Popup>
                          <div style={{ fontSize: 12, lineHeight: 1.6 }}>
                            <strong>{h.id}</strong><br />
                            CH₄: <strong>{h.ch4.toFixed(1)} ppb</strong><br />
                            Anomaly σ: {h.score.toFixed(3)}<br />
                            Severity: {h.severity}<br />
                            {h.distanceKm != null && <>Distance: {h.distanceKm} km<br /></>}
                            {h.lat.toFixed(4)}°N, {h.lng.toFixed(4)}°E
                          </div>
                        </Popup>
                      </CircleMarker>
                    ))}
                  </MapContainer>
                </div>
                <div className="flex items-center gap-4 mt-3 text-xs flex-wrap">
                  <span className="flex items-center gap-1.5 text-info-blue">
                    <span className="w-3 h-3 rounded-full border-2 border-info-blue shrink-0" style={{ display: 'inline-block' }} />
                    Search radius
                  </span>
                  {Object.entries(SEV_COLOR).map(([sev, col]) => (
                    <span key={sev} className="flex items-center gap-1.5 text-gray-400">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: col, display: 'inline-block' }} />
                      {sev}
                    </span>
                  ))}
                  {todayTile && (
                    <span className="flex items-center gap-1.5 text-info-blue">
                      <span className="w-3 h-2 rounded-sm shrink-0" style={{ background: 'linear-gradient(90deg,#fff3e0,#e53935)', border: '1px solid #3b82f6', display: 'inline-block' }} />
                      CH₄ heatmap
                    </span>
                  )}
                  <span className="ml-auto text-gray-500">
                    {filtered.length} hotspot{filtered.length !== 1 ? 's' : ''} shown
                  </span>
                </div>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
              <Card>
                <CardTitle>Top 10 by CH₄ ppb</CardTitle>
                {top10.length === 0 ? (
                  <div className="h-48 flex items-center justify-center text-gray-500 text-sm">No data</div>
                ) : (
                  <ResponsiveContainer width="100%" height={340}>
                    <BarChart data={top10} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                      <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                      <YAxis dataKey="name" type="category" tick={{ fill: '#9ca3af', fontSize: 11 }}
                        axisLine={false} tickLine={false} width={34} />
                      <Tooltip content={<DarkTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                      <Bar dataKey="ch4" name="CH₄ (ppb)" radius={[0, 4, 4, 0]}>
                        {top10.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Card>
            </motion.div>
          </div>

          {/* ── Historical date-range map ───────────────────────────────────── */}
          {histTile && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <Card>
                <CardTitle>Historical CH₄ Overlay — {fromDate} to {toDate}</CardTitle>
                <div className="rounded-xl overflow-hidden border border-dark-border" style={{ height: 300 }}>
                  <MapContainer
                    key={`hist-${mapCenter[0]}-${mapCenter[1]}-${radiusKm}`}
                    center={mapCenter} zoom={mapZoom}
                    style={{ height: '100%', width: '100%' }}
                    scrollWheelZoom zoomControl attributionControl={false}>
                    <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
                    <TileLayer url={histTile} opacity={0.65} attribution="Copernicus Sentinel-5P" />
                    {center && (
                      <Circle
                        center={[center.lat, center.lng]}
                        radius={center.radius_km * 1000}
                        pathOptions={{ color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.05, weight: 1.5, dashArray: '6 4' }}
                      />
                    )}
                    {center && (
                      <Marker position={[center.lat, center.lng]}>
                        <Popup><strong>{facilityInfo?.name}</strong></Popup>
                      </Marker>
                    )}
                    {filtered.map(h => (
                      <CircleMarker key={h.id}
                        center={[h.lat, h.lng]}
                        radius={h.priority === 1 ? 9 : h.priority === 2 ? 6 : 4}
                        pathOptions={{
                          color: SEV_COLOR[h.severity], fillColor: SEV_COLOR[h.severity],
                          fillOpacity: 0.75, weight: h.priority === 1 ? 2 : 1,
                        }}>
                        <Popup>
                          <div style={{ fontSize: 12 }}>
                            <strong>{h.id}</strong> · {h.ch4.toFixed(1)} ppb · σ {h.score.toFixed(3)}
                          </div>
                        </Popup>
                      </CircleMarker>
                    ))}
                  </MapContainer>
                </div>
              </Card>
            </motion.div>
          )}

          {/* ── Data table ─────────────────────────────────────────────────── */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
            <DataTable
              columns={columns}
              data={filtered}
              searchPlaceholder="Search by ID, severity…"
              onRowClick={row => setSelectedEmitter(row)}
              pageSize={10}
            />
          </motion.div>
        </>
      )}

      {/* ── Empty state before first analysis ────────────────────────────── */}
      {!analysisRun && !loading && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="flex flex-col items-center justify-center py-24 text-center">
          <Satellite className="w-16 h-16 text-gray-700 mb-4" />
          <p className="text-gray-500 text-lg font-medium">Select a facility and run an analysis</p>
          <p className="text-gray-600 text-sm mt-1 max-w-md">
            Search for a company or facility above, choose your date range and radius,
            then click <strong className="text-info-blue">Analyse with Earth Engine</strong> to visualise CH₄ concentrations.
          </p>
        </motion.div>
      )}

      {/* ── Loading overlay ──────────────────────────────────────────────── */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <Spinner size="lg" className="text-info-blue" />
          <p className="text-gray-400 text-sm">Querying Google Earth Engine for Sentinel-5P TROPOMI data…</p>
          <p className="text-gray-600 text-xs">This may take 30–90 seconds depending on the area and date range.</p>
        </div>
      )}

      {/* ── Detail modal ─────────────────────────────────────────────────── */}
      <AnimatePresence>
        {selectedEmitter && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedEmitter(null)}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-card w-full max-w-lg max-h-[90vh] overflow-y-auto"
              onClick={e => e.stopPropagation()}>

              <div className="p-5 border-b border-dark-border flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                    style={{ background: `${SEV_COLOR[selectedEmitter.severity]}22` }}>
                    <MapPin className="w-5 h-5" style={{ color: SEV_COLOR[selectedEmitter.severity] }} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-accent-green text-sm">{selectedEmitter.id}</span>
                      <StatusBadge status={selectedEmitter.status} />
                      <span className="px-1.5 py-0.5 rounded text-xs font-semibold bg-info-blue/20 text-info-blue">S5P</span>
                    </div>
                    <p className="text-white font-semibold">{selectedEmitter.location}</p>
                  </div>
                </div>
                <button onClick={() => setSelectedEmitter(null)}
                  className="p-2 hover:bg-dark-border rounded-lg text-gray-400 hover:text-white transition-colors shrink-0">✕
                </button>
              </div>

              <div className="p-5 space-y-5">
                {/* Metric cards */}
                <div className="grid grid-cols-3 gap-3">
                  {[
                    {
                      label: 'CH₄ (ppb)',
                      value: selectedEmitter.ch4.toFixed(1),
                      unit: 'ppb',
                      color: SEV_COLOR[selectedEmitter.severity],
                    },
                    {
                      label: 'Anomaly σ',
                      value: selectedEmitter.score.toFixed(3),
                      unit: '',
                      color: selectedEmitter.score > 3 ? '#ef4444' : selectedEmitter.score > 2 ? '#f59e0b' : '#22c55e',
                    },
                    {
                      label: 'Priority',
                      value: PRI_LABEL[selectedEmitter.priority],
                      unit: '',
                      color: PRI_COLOR[selectedEmitter.priority],
                    },
                  ].map(({ label, value, unit, color }) => (
                    <div key={label} className="bg-dark-bg/60 rounded-xl p-3 text-center">
                      <p className="text-xs text-gray-500 mb-1">{label}</p>
                      <p className="text-base font-bold leading-tight" style={{ color }}>
                        {value}{unit && <span className="text-xs text-gray-500 ml-1">{unit}</span>}
                      </p>
                    </div>
                  ))}
                </div>

                {/* Anomaly bar */}
                <div>
                  <div className="flex justify-between text-xs text-gray-500 mb-1.5">
                    <span>Anomaly Score Strength</span>
                    <span>{selectedEmitter.score.toFixed(3)} σ (out of 5)</span>
                  </div>
                  <div className="h-2.5 bg-dark-border rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(100, (selectedEmitter.score / 5) * 100)}%` }}
                      transition={{ duration: 0.5, ease: 'easeOut' }}
                      className="h-full rounded-full"
                      style={{ background: SEV_COLOR[selectedEmitter.severity] }}
                    />
                  </div>
                </div>

                {/* Details grid */}
                <div className="grid grid-cols-2 gap-y-3 gap-x-4">
                  {[
                    ['Latitude',    `${selectedEmitter.lat.toFixed(5)}°N`],
                    ['Longitude',   `${selectedEmitter.lng.toFixed(5)}°E`],
                    ['Severity',     selectedEmitter.severity],
                    ['Distance',     selectedEmitter.distanceKm != null ? `${selectedEmitter.distanceKm} km` : '—'],
                    ['Facility',     facilityInfo?.name || '—'],
                    ['Operator',     facilityInfo?.operator || '—'],
                    ['Satellite',   'Sentinel-5P TROPOMI'],
                    ['Period',      `${fromDate} → ${toDate}`],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <p className="text-xs text-gray-500">{k}</p>
                      <p className="text-sm text-white font-medium mt-0.5">{v}</p>
                    </div>
                  ))}
                </div>

                {/* Inline mini-map */}
                <div>
                  <p className="text-xs text-gray-500 mb-2">Location Preview</p>
                  <div className="rounded-xl overflow-hidden border border-dark-border" style={{ height: 190 }}>
                    <MapContainer
                      center={[selectedEmitter.lat, selectedEmitter.lng]} zoom={10}
                      style={{ height: '100%', width: '100%' }}
                      scrollWheelZoom={false} zoomControl={false} attributionControl={false}>
                      <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
                      {todayTile && <TileLayer url={todayTile} opacity={0.6} />}
                      <CircleMarker
                        center={[selectedEmitter.lat, selectedEmitter.lng]}
                        radius={13}
                        pathOptions={{
                          color:       SEV_COLOR[selectedEmitter.severity],
                          fillColor:   SEV_COLOR[selectedEmitter.severity],
                          fillOpacity: 0.7,
                          weight:      2.5,
                        }}>
                        <Popup>{selectedEmitter.id} — {selectedEmitter.severity}</Popup>
                      </CircleMarker>
                      {/* Show facility marker */}
                      {center && (
                        <Marker position={[center.lat, center.lng]}>
                          <Popup><strong>{facilityInfo?.name}</strong></Popup>
                        </Marker>
                      )}
                    </MapContainer>
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default SuperEmitters
