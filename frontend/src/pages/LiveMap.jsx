import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet'
import L from 'leaflet'
import {
  Layers,
  Filter,
  RefreshCw,
  MapPin,
  AlertTriangle,
  Clock,
  Activity,
  X,
  Navigation2,
  Crosshair,
  Thermometer,
  Building2,
  Sparkles,
} from 'lucide-react'
import { geeService, geojsonService, facilitiesService, heatmapFallbackService, detectedHotspotsService } from '../services/api'
import { StatusBadge } from '../components/ui/AlertCard'
import HeatmapLayer from '../components/map/HeatmapLayer'
import { mockHeatmapPoints } from '../data/mockData'

// ─── Leaflet marker icons ────────────────────────────────────────────────

const riskColors = {
  Critical: '#ef4444',
  High: '#f97316',
  Medium: '#eab308',
  Low: '#22c55e',
}

const makeIcon = (color) =>
  L.divIcon({
    className: '',
    html: `
      <div style="
        width:8px;height:8px;border-radius:50%;
        background:${color};border:1.5px solid rgba(255,255,255,0.8);
        box-shadow:0 0 4px ${color}99;
      "></div>`,
    iconSize: [8, 8],
    iconAnchor: [4, 4],
    popupAnchor: [0, -6],
  })

const markerIcons = Object.fromEntries(
  Object.entries(riskColors).map(([k, v]) => [k, makeIcon(v)]),
)

const userLocationIcon = L.divIcon({
  className: '',
  html: `
    <div style="
      width:18px;height:18px;border-radius:50%;
      background:#3b82f6;border:3px solid #fff;
      box-shadow:0 0 12px #3b82f688;
    "></div>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
  popupAnchor: [0, -12],
})

// ─── Fly to location helper ──────────────────────────────────────────────

const FlyToLocation = ({ position, trigger }) => {
  const map = useMap()
  useEffect(() => {
    if (position && trigger) map.flyTo(position, 14, { duration: 1.5 })
  }, [position, trigger, map])
  return null
}

// ─── GEE Tile Overlay (uses TileLayer with GEE-generated URL) ────────────

const GEETileOverlay = ({ tileUrl }) => {
  if (!tileUrl) return null
  return (
    <TileLayer
      url={tileUrl}
      attribution="Copernicus Sentinel-5P"
      opacity={0.65}
      zIndex={10}
    />
  )
}

// ─── Layer control panel ─────────────────────────────────────────────────

const LayerPanel = ({ layers, setLayers, onClose }) => {
  const toggle = (key) => setLayers((prev) => ({ ...prev, [key]: !prev[key] }))

  const layerDefs = [
    { key: 'heatmap', label: 'CH\u2084 Heatmap', desc: 'Sentinel-5P concentration', icon: Thermometer },
    { key: 'geeTiles', label: 'Satellite Overlay', desc: 'Sentinel-5P raster tiles', icon: Layers },
    { key: 'markers', label: 'Facility Markers', desc: 'Industry facility locations', icon: Building2 },
    { key: 'circles', label: 'Facility Radius', desc: 'Context rings around facilities', icon: Activity },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="glass-card p-4 w-64"
    >
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-semibold text-white text-sm">Map Layers</h4>
        <button onClick={onClose}><X className="w-4 h-4 text-gray-400" /></button>
      </div>
      <div className="space-y-3">
        {layerDefs.map(({ key, label, desc, icon: Icon }) => (
          <label key={key} className="flex items-center gap-3 cursor-pointer group">
            <button
              onClick={() => toggle(key)}
              className={`w-9 h-5 rounded-full relative transition-colors ${layers[key] ? 'bg-accent-green' : 'bg-dark-border'
                }`}
            >
              <span
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${layers[key] ? 'left-[18px]' : 'left-0.5'
                  }`}
              />
            </button>
            <div>
              <div className="flex items-center gap-1.5">
                <Icon className="w-3.5 h-3.5 text-gray-400" />
                <span className="text-sm text-gray-200">{label}</span>
              </div>
              <span className="text-[11px] text-gray-500">{desc}</span>
            </div>
          </label>
        ))}
      </div>
    </motion.div>
  )
}

// ─── Map controls ────────────────────────────────────────────────────────

const MapControls = ({
  filters, setFilters, layers, setLayers,
  onRefresh, onLocateMe, isLocating, isLoadingHeatmap,
  anomalyMode, setAnomalyMode,
}) => {
  const [showFilters, setShowFilters] = useState(false)
  const [showLayers, setShowLayers] = useState(false)

  return (
    <div className="absolute top-4 right-4 z-[1000] flex flex-col gap-2 items-end">
      <div className="glass-card p-2 flex flex-col gap-2">
        <button onClick={onLocateMe} disabled={isLocating}
          className={`p-2 rounded-lg transition-colors ${isLocating ? 'bg-info-blue/20 text-info-blue' : 'hover:bg-dark-border text-gray-400 hover:text-white'
            }`} title="My Location">
          <Crosshair className={`w-5 h-5 ${isLocating ? 'animate-pulse' : ''}`} />
        </button>
        <button onClick={onRefresh}
          className="p-2 hover:bg-dark-border rounded-lg transition-colors" title="Refresh Data">
          <RefreshCw className={`w-5 h-5 text-gray-400 hover:text-white ${isLoadingHeatmap ? 'animate-spin' : ''}`} />
        </button>
        <button onClick={() => { setShowFilters(!showFilters); setShowLayers(false) }}
          className={`p-2 rounded-lg transition-colors ${showFilters ? 'bg-accent-green/20 text-accent-green' : 'hover:bg-dark-border text-gray-400 hover:text-white'
            }`} title="Filters">
          <Filter className="w-5 h-5" />
        </button>
        <button onClick={() => { setShowLayers(!showLayers); setShowFilters(false) }}
          className={`p-2 rounded-lg transition-colors ${showLayers ? 'bg-accent-green/20 text-accent-green' : 'hover:bg-dark-border text-gray-400 hover:text-white'
            }`} title="Layers">
          <Layers className="w-5 h-5" />
        </button>
      </div>

      <AnimatePresence>
        {showFilters && (
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
            className="glass-card p-4 w-64">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-semibold text-white text-sm">Filters</h4>
              <button onClick={() => setShowFilters(false)}><X className="w-4 h-4 text-gray-400" /></button>
            </div>
            <div className="space-y-4">
              <div className="pb-3 border-b border-dark-border">
                <label className="text-sm text-gray-400 mb-2 block">Heatmap Mode</label>
                <button
                  onClick={() => setAnomalyMode((v) => !v)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg border text-xs font-semibold transition-colors ${anomalyMode
                      ? 'bg-orange-600/20 text-orange-300 border-orange-500/40'
                      : 'bg-dark-card/70 text-gray-300 border-dark-border hover:border-accent-green/40'
                    }`}
                >
                  <span className="flex items-center gap-2">
                    <Sparkles className="w-3.5 h-3.5" />
                    {anomalyMode ? 'Anomaly Only' : 'Raw CH4 Samples'}
                  </span>
                  <span className={`w-2 h-2 rounded-full ${anomalyMode ? 'bg-orange-400' : 'bg-cyan-400'}`} />
                </button>
              </div>

              <div>
                <label className="text-sm text-gray-400 mb-2 block">Risk Level</label>
                <div className="space-y-2">
                  {['Critical', 'High', 'Medium', 'Low'].map((level) => (
                    <label key={level} className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={filters.riskLevels.includes(level)}
                        onChange={(e) => {
                          setFilters((prev) => ({
                            ...prev,
                            riskLevels: e.target.checked
                              ? [...prev.riskLevels, level]
                              : prev.riskLevels.filter((l) => l !== level),
                          }))
                        }}
                        className="w-4 h-4 rounded border-dark-border bg-dark-bg text-accent-green focus:ring-accent-green"
                      />
                      <span className="text-sm text-gray-300">{level}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {showLayers && (
          <LayerPanel layers={layers} setLayers={setLayers} onClose={() => setShowLayers(false)} />
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Heatmap legend ──────────────────────────────────────────────────────

const HeatmapLegend = ({ stats }) => {
  const gradient = 'linear-gradient(to right, #fff3e0, #ffcc80, #ffa040, #f36f21, #e53935, #b71c1c, #7f0000)'

  return (
    <div className="absolute bottom-4 left-4 z-[1000] glass-card p-4 w-64">
      <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
        <Thermometer className="w-4 h-4 text-red-400" />
        CH&#x2084; Concentration
      </h4>

      {/* Gradient bar */}
      <div className="h-3 rounded-full mb-2" style={{ background: gradient }} />
      <div className="flex justify-between text-[10px] text-gray-400 mb-3">
        <span>{stats?.min ? `${stats.min} ppb` : 'Low'}</span>
        <span>{stats?.max ? `${stats.max} ppb` : 'High'}</span>
      </div>

      {/* Stats */}
      {stats?.count > 0 && (
        <div className="border-t border-dark-border pt-2 space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Mean</span>
            <span className="text-gray-300">{stats.mean} ppb</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Std Dev</span>
            <span className="text-gray-300">&plusmn;{stats.std} ppb</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Samples</span>
            <span className="text-gray-300">{stats.count.toLocaleString()}</span>
          </div>
        </div>
      )}

      {/* Marker legend */}
      <div className="border-t border-dark-border pt-3 mt-3">
        <h5 className="text-xs font-medium text-gray-400 mb-2">Risk Levels</h5>
        <div className="grid grid-cols-2 gap-1.5">
          {Object.entries(riskColors).map(([label, color]) => (
            <div key={label} className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full border border-white/30" style={{ backgroundColor: color }} />
              <span className="text-[11px] text-gray-400">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Facility Quick-Toggle Bar ──────────────────────────────────────────

const FacilityToggleBar = ({ layers, setLayers, anomalyMode, setAnomalyMode }) => {
  const toggleLayer = (key) => setLayers((prev) => ({ ...prev, [key]: !prev[key] }))

  const btns = [
    {
      key: 'heatmap',
      activeLabel: 'Heatmap ON',
      inactiveLabel: 'Heatmap OFF',
      activeStyle: 'bg-red-600 text-white border-red-500 shadow-lg shadow-red-900/40',
      inactiveStyle: 'bg-dark-card/80 text-gray-400 border-dark-border hover:border-red-600/50 hover:text-red-400',
      dot: 'bg-red-400',
      icon: Thermometer,
    },
    {
      key: 'markers',
      activeLabel: 'Facilities ON',
      inactiveLabel: 'Facilities OFF',
      activeStyle: 'bg-amber-600 text-white border-amber-500 shadow-lg shadow-amber-900/40',
      inactiveStyle: 'bg-dark-card/80 text-gray-400 border-dark-border hover:border-amber-500/50 hover:text-amber-400',
      dot: 'bg-amber-400',
      icon: MapPin,
    },
    {
      key: 'circles',
      activeLabel: 'Radius ON',
      inactiveLabel: 'Radius OFF',
      activeStyle: 'bg-orange-600 text-white border-orange-500 shadow-lg shadow-orange-900/40',
      inactiveStyle: 'bg-dark-card/80 text-gray-400 border-dark-border hover:border-orange-500/50 hover:text-orange-400',
      dot: 'bg-orange-400',
      icon: Activity,
    },
  ]

  const anomalyBtn = {
    activeLabel: 'Anomaly ON',
    inactiveLabel: 'Anomaly OFF',
    activeStyle: 'bg-violet-600 text-white border-violet-500 shadow-lg shadow-violet-900/40',
    inactiveStyle: 'bg-dark-card/80 text-gray-400 border-dark-border hover:border-violet-500/50 hover:text-violet-400',
    dot: 'bg-violet-400',
    icon: Sparkles,
  }
  const AnomalyIcon = anomalyBtn.icon

  return (
    <div className="absolute top-[4.5rem] left-1/2 -translate-x-1/2 z-[1000] flex gap-2">
      {btns.filter((b) => b.key !== 'circles').map(({ key, activeLabel, inactiveLabel, activeStyle, inactiveStyle, dot, icon: Icon }) => {
        const on = layers[key]
        return (
          <button
            key={key}
            onClick={() => toggleLayer(key)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold transition-all duration-200 backdrop-blur-md ${on ? activeStyle : inactiveStyle
              }`}
          >
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${on ? dot : 'bg-gray-600'
              }`} />
            <Icon className="w-3.5 h-3.5" />
            {on ? activeLabel : inactiveLabel}
          </button>
        )
      })}

      <button
        onClick={() => setAnomalyMode((v) => !v)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold transition-all duration-200 backdrop-blur-md ${anomalyMode ? anomalyBtn.activeStyle : anomalyBtn.inactiveStyle}`}
      >
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${anomalyMode ? anomalyBtn.dot : 'bg-gray-600'}`} />
        <AnomalyIcon className="w-3.5 h-3.5" />
        {anomalyMode ? anomalyBtn.activeLabel : anomalyBtn.inactiveLabel}
      </button>
    </div>
  )
}

// ─── Main LiveMap component ──────────────────────────────────────────────

const LiveMap = () => {
  const [selectedMarker, setSelectedMarker] = useState(null)
  const [filters, setFilters] = useState({
    riskLevels: ['Low'],
  })
  const [layers, setLayers] = useState({
    heatmap: true,     // leaflet.heat point heatmap (default ON)
    geeTiles: false,   // GEE raster tile overlay
    markers: true,     // point markers
    circles: false,    // emission circles
  })
  const [isLoading, setIsLoading] = useState(false)
  const [mapMarkers, setMapMarkers] = useState([])

  // Heatmap state
  const [heatmapPoints, setHeatmapPoints] = useState([])
  const [heatmapStats, setHeatmapStats] = useState(null)
  const [geeTileUrl, setGeeTileUrl] = useState(null)
  const [isLoadingHeatmap, setIsLoadingHeatmap] = useState(false)
  const [heatmapError, setHeatmapError] = useState(null)
  const [anomalyMode, setAnomalyMode] = useState(false)

  // User location
  const [userLocation, setUserLocation] = useState(null)
  const [locationError, setLocationError] = useState(null)
  const [isLocating, setIsLocating] = useState(false)
  const [flyToTrigger, setFlyToTrigger] = useState(0)

  // ── Fetch heatmap data: GEE + DB fallback fire in parallel ──────────

  const fetchHeatmapData = useCallback(async () => {
    setIsLoadingHeatmap(true)
    setHeatmapError(null)

    if (anomalyMode) {
      try {
        const now = new Date()
        const start = new Date(now)
        start.setDate(now.getDate() - 30)
        const fmt = (d) => d.toISOString().slice(0, 10)

        const [anomalyRes, tileRes, detectedRes] = await Promise.allSettled([
          geeService.getHotspots(fmt(start), fmt(now), 1000, 20000),
          geeService.getCH4Tiles(30),
          detectedHotspotsService.getAll({ ordering: '-anomaly_score', page_size: 1000 }),
        ])

        if (tileRes.status === 'fulfilled' && tileRes.value?.tile_url) {
          setGeeTileUrl(tileRes.value.tile_url)
        }

        if (anomalyRes.status === 'fulfilled' && Array.isArray(anomalyRes.value?.hotspots) && anomalyRes.value.hotspots.length > 0) {
          const hotspots = anomalyRes.value.hotspots
          const maxSigma = Math.max(...hotspots.map((h) => Number(h.anomaly_score || 0)), 1)
          const points = hotspots.map((h) => {
            const sigma = Number(h.anomaly_score || 0)
            const intensity = Math.max(0.15, Math.min(1, sigma / maxSigma))
            return [Number(h.latitude), Number(h.longitude), intensity]
          })
          setHeatmapPoints(points)
          setHeatmapStats({
            mean: anomalyRes.value?.stats?.mean,
            std: anomalyRes.value?.stats?.std,
            min: anomalyRes.value?.stats?.min,
            max: anomalyRes.value?.stats?.max,
            count: hotspots.length,
          })
          setIsLoadingHeatmap(false)
          return
        }

        if (detectedRes.status === 'fulfilled' && Array.isArray(detectedRes.value) && detectedRes.value.length > 0) {
          const rows = detectedRes.value.filter((h) => h.latitude && h.longitude)
          const maxSigma = Math.max(...rows.map((h) => Number(h.anomaly_score || 0)), 1)
          const points = rows.map((h) => {
            const sigma = Number(h.anomaly_score || 0)
            const intensity = Math.max(0.15, Math.min(1, sigma / maxSigma))
            return [Number(h.latitude), Number(h.longitude), intensity]
          })
          setHeatmapPoints(points)
          setHeatmapStats({ count: points.length })
          setIsLoadingHeatmap(false)
          return
        }

        setHeatmapPoints([])
        setHeatmapStats({ count: 0 })
        setHeatmapError('No anomaly points available for the selected period.')
      } catch (err) {
        setHeatmapError('Failed to load anomaly heatmap.')
        setHeatmapPoints([])
        setHeatmapStats({ count: 0 })
      } finally {
        setIsLoadingHeatmap(false)
      }
      return
    }

    console.groupCollapsed('%c[Heatmap] fetchHeatmapData started', 'color:#22d3ee;font-weight:bold')
    console.log('[Heatmap] Firing 3 requests in parallel:')
    console.log('  → GEE heatmap  : GET /api/gee/ch4-heatmap/?days=30&num_points=1000&scale=20000')
    console.log('  → GEE tiles    : GET /api/gee/ch4-tiles/?days=30')
    console.log('  → DB fallback  : GET /api/heatmap/fallback/')
    const t0 = performance.now()

    // All three requests fire simultaneously.
    // GEE heatmap has a 12 s timeout so the DB fallback wins immediately
    // when GEE is unavailable – no sequential wait.
    const [heatmapRes, tileRes, fallbackRes] = await Promise.allSettled([
      geeService.getCH4Heatmap(30, 1000, 20000),
      geeService.getCH4Tiles(30),
      heatmapFallbackService.getPoints(),
    ])

    const elapsed = (performance.now() - t0).toFixed(0)
    console.log(`[Heatmap] All requests settled in ${elapsed} ms`)

    // ── Log each result ───────────────────────────────────────────────
    console.group('[Heatmap] GEE ch4-heatmap result')
    console.log('  status :', heatmapRes.status)
    if (heatmapRes.status === 'fulfilled') {
      const v = heatmapRes.value
      console.log('  points returned :', v?.points?.length ?? 0)
      console.log('  stats           :', v?.stats)
      if (v?.points?.length > 0) console.log('  first 3 points  :', v.points.slice(0, 3))
    } else {
      console.error('  REJECTED – reason:', heatmapRes.reason?.message ?? heatmapRes.reason)
      console.error('  axios response  :', heatmapRes.reason?.response?.data)
      console.error('  HTTP status     :', heatmapRes.reason?.response?.status)
    }
    console.groupEnd()

    console.group('[Heatmap] GEE ch4-tiles result')
    console.log('  status :', tileRes.status)
    if (tileRes.status === 'fulfilled') {
      console.log('  tile_url :', tileRes.value?.tile_url ?? '(none)')
    } else {
      console.error('  REJECTED – reason:', tileRes.reason?.message ?? tileRes.reason)
      console.error('  HTTP status     :', tileRes.reason?.response?.status)
      console.error('  response data   :', tileRes.reason?.response?.data)
    }
    console.groupEnd()

    console.group('[Heatmap] DB fallback result')
    console.log('  status :', fallbackRes.status)
    if (fallbackRes.status === 'fulfilled') {
      const v = fallbackRes.value
      console.log('  points returned :', v?.points?.length ?? 0)
      console.log('  source          :', v?.source)
      console.log('  stats           :', v?.stats)
      if (v?.points?.length > 0) console.log('  first 3 points  :', v.points.slice(0, 3))
    } else {
      console.error('  REJECTED – reason:', fallbackRes.reason?.message ?? fallbackRes.reason)
      console.error('  HTTP status     :', fallbackRes.reason?.response?.status)
      console.error('  response data   :', fallbackRes.reason?.response?.data)
    }
    console.groupEnd()

    // ── GEE tile overlay (independent of heatmap) ───────────────────
    if (tileRes.status === 'fulfilled' && tileRes.value?.tile_url) {
      console.log('[Heatmap] ✔ GEE tile overlay URL set')
      setGeeTileUrl(tileRes.value.tile_url)
    } else {
      console.warn('[Heatmap] ✗ GEE tile overlay not available')
    }

    // ── Prefer GEE heatmap; fall back to DB instantly ────────────────
    const geeOk = heatmapRes.status === 'fulfilled' && heatmapRes.value?.points?.length > 0
    const dbOk  = fallbackRes.status === 'fulfilled' && fallbackRes.value?.points?.length > 0

    console.log('[Heatmap] Decision flags — geeOk:', geeOk, ' dbOk:', dbOk)

    if (geeOk) {
      // GEE data is fresh satellite data – use it
      console.log('%c[Heatmap] ✔ Using LIVE GEE data', 'color:#22c55e;font-weight:bold',
        heatmapRes.value.points.length, 'points')
      setHeatmapPoints(heatmapRes.value.points)
      setHeatmapStats(heatmapRes.value.stats)
    } else if (dbOk) {
      // Satellite unavailable – DB fallback already finished in parallel
      console.warn('%c[Heatmap] ⚠ Using DB fallback data', 'color:#f59e0b;font-weight:bold',
        fallbackRes.value.points.length, 'points')
      setHeatmapPoints(fallbackRes.value.points)
      setHeatmapStats(fallbackRes.value.stats)
    } else {
      // Both satellite and backend unavailable – use embedded CSV-derived demo data
      console.warn('%c[Heatmap] Using embedded demo data', 'color:#f59e0b;font-weight:bold',
        mockHeatmapPoints.length, 'points')
      setHeatmapPoints(mockHeatmapPoints)
      setHeatmapStats({ mean: 1847, std: 42, min: 1800, max: 1950, count: mockHeatmapPoints.length })
    }

    console.groupEnd()
    setIsLoadingHeatmap(false)
  }, [anomalyMode])

  // ── Fetch facility marker data from backend ─────────────────────────

  const fetchMarkerData = useCallback(async () => {
    setIsLoading(true)
    try {
      const facilitiesGeo = await geojsonService.getFacilities().catch(() => null)

      const markers = []
      let id = 1

      if (facilitiesGeo?.features) {
        for (const f of facilitiesGeo.features) {
          const c = f.geometry?.coordinates
          if (!c) continue
          const ftype = f.properties?.type || 'facility'
          const fname = f.properties?.name || 'Unknown Facility'
          markers.push({
            id: id++,
            position: [c[1], c[0]],
            name: `${fname}`,
            subLabel: ftype.charAt(0).toUpperCase() + ftype.slice(1).replace('_', ' '),
            emission: null,
            riskLevel: 'Low',
            lastDetected: 'N/A',
            type: 'facility',
            operator: f.properties?.operator || 'Unknown',
            status: f.properties?.status || 'active',
          })
        }
      }

      if (markers.length === 0) {
        const facilities = await facilitiesService.getAll({ ordering: 'facility_id', page_size: 2000 })
        const list = Array.isArray(facilities) ? facilities : []
        list.forEach((f, i) => {
          if (f.latitude && f.longitude) {
            const ftype = f.type || 'facility'
            markers.push({
              id: i + 1,
              position: [Number(f.latitude), Number(f.longitude)],
              name: f.name || `Facility ${i + 1}`,
              subLabel: ftype.charAt(0).toUpperCase() + ftype.slice(1).replace('_', ' '),
              emission: null,
              riskLevel: 'Low',
              lastDetected: 'N/A',
              type: 'facility',
              operator: f.operator || 'Unknown',
              status: f.status || 'active',
            })
          }
        })
      }

      setMapMarkers(markers)
    } catch (err) {
      console.error('Map marker fetch error:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // ── Initial data load ───────────────────────────────────────────────

  useEffect(() => {
    fetchHeatmapData()
    fetchMarkerData()
  }, [fetchHeatmapData, fetchMarkerData])

  // ── User location ───────────────────────────────────────────────────

  const getUserLocation = () => {
    if (!navigator.geolocation) {
      setLocationError('Geolocation not supported')
      return
    }
    setIsLocating(true)
    setLocationError(null)

    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setUserLocation({ lat: coords.latitude, lng: coords.longitude, accuracy: coords.accuracy })
        setFlyToTrigger((p) => p + 1)
        setIsLocating(false)
      },
      (err) => {
        setIsLocating(false)
        const msgs = {
          1: 'Location permission denied.',
          2: 'Location unavailable.',
          3: 'Location request timed out.',
        }
        setLocationError(msgs[err.code] || 'Unknown location error.')
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    )
  }

  useEffect(() => {
    if (!navigator.geolocation) return
    const id = navigator.geolocation.watchPosition(
      ({ coords }) => setUserLocation({ lat: coords.latitude, lng: coords.longitude, accuracy: coords.accuracy }),
      () => { },
      { enableHighAccuracy: true, timeout: 30000, maximumAge: 10000 },
    )
    return () => navigator.geolocation.clearWatch(id)
  }, [])

  // ── Derived data ────────────────────────────────────────────────────

  const filteredMarkers = mapMarkers.filter((m) => filters.riskLevels.includes(m.riskLevel))

  const handleRefresh = () => {
    fetchHeatmapData()
    fetchMarkerData()
  }

  const defaultCenter = [22.5937, 78.9629]
  const defaultZoom = 5

  // ── Render ──────────────────────────────────────────────────────────

  return (
    <div className="h-[calc(100vh-7rem)] relative">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-[1000] p-4 bg-gradient-to-b from-dark-bg to-transparent pointer-events-none">
        <div className="pointer-events-auto inline-block">
          <h1 className="text-2xl font-bold text-white">Live Detection Map</h1>
          <p className="text-gray-400 text-sm mt-1">
            {anomalyMode ? 'Anomaly-only methane heatmap (z-score filtered)' : 'Real-time methane heatmap from Sentinel-5P TROPOMI'}
            {heatmapStats?.count ? ` \u2022 ${heatmapStats.count.toLocaleString()} samples` : ''}
            {filteredMarkers.length > 0 ? ` \u2022 ${filteredMarkers.length} facilities` : ''}
          </p>
        </div>
      </div>

      {/* ━━━ Map ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        className="w-full h-full rounded-xl overflow-hidden"
        style={{ background: '#0f172a' }}
      >
        {/* Base dark tiles */}
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* GEE raster tile overlay */}
        {layers.geeTiles && geeTileUrl && <GEETileOverlay tileUrl={geeTileUrl} />}

        {/* leaflet.heat heatmap – red-orange theme */}
        {layers.heatmap && heatmapPoints.length > 0 && (
          <HeatmapLayer
            points={heatmapPoints}
            options={{
              radius: 12,
              blur: 8,
              maxZoom: 12,
              max: 1.0,
              minOpacity: 0.22,
              gradient: {
                0.0: '#fff3e0',
                0.15: '#ffcc80',
                0.3: '#ffa040',
                0.5: '#f36f21',
                0.7: '#e53935',
                0.85: '#b71c1c',
                1.0: '#7f0000',
              },
            }}
          />
        )}

        {/* Fly-to helper */}
        <FlyToLocation
          position={userLocation ? [userLocation.lat, userLocation.lng] : null}
          trigger={flyToTrigger}
        />

        {/* User location */}
        {userLocation && (
          <>
            <Marker position={[userLocation.lat, userLocation.lng]} icon={userLocationIcon}>
              <Popup>
                <div className="min-w-[180px]">
                  <div className="flex items-center gap-2 mb-2">
                    <Navigation2 className="w-4 h-4 text-info-blue" />
                    <h3 className="font-semibold text-white text-sm">Your Location</h3>
                  </div>
                  <div className="space-y-1 text-xs text-gray-400">
                    <p>Lat: {userLocation.lat.toFixed(6)}</p>
                    <p>Lng: {userLocation.lng.toFixed(6)}</p>
                    {userLocation.accuracy && <p>Accuracy: &plusmn;{Math.round(userLocation.accuracy)}m</p>}
                  </div>
                </div>
              </Popup>
            </Marker>
            <Circle
              center={[userLocation.lat, userLocation.lng]}
              radius={userLocation.accuracy || 100}
              pathOptions={{ color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.1, weight: 1, dashArray: '5,5' }}
            />
          </>
        )}

        {/* Facility markers */}
        {layers.markers && filteredMarkers.map((m) => (
          <Marker key={m.id} position={m.position} icon={markerIcons[m.riskLevel]}
            eventHandlers={{ click: () => setSelectedMarker(m) }}>
            <Popup className="custom-popup">
              <div className="min-w-[250px]">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-white text-sm">{m.name}</h3>
                    {m.subLabel && (
                      <p className="text-[11px] text-gray-500 mt-0.5">{m.subLabel}</p>
                    )}
                  </div>
                  <StatusBadge status={m.riskLevel} />
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-gray-400">
                    <MapPin className="w-4 h-4" />
                    <span>{m.position[0].toFixed(4)}, {m.position[1].toFixed(4)}</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <Activity className="w-4 h-4" />
                    <span>Operator: <span className="text-white font-medium">{m.operator || 'Unknown'}</span></span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <Clock className="w-4 h-4" />
                    <span>Status: {m.status || 'active'}</span>
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-dark-border flex gap-2">
                  <button className="flex-1 px-3 py-1.5 bg-accent-green/20 text-accent-green text-xs font-medium rounded hover:bg-accent-green/30 transition-colors">
                    View Details
                  </button>
                  <button className="flex-1 px-3 py-1.5 bg-dark-border text-gray-300 text-xs font-medium rounded hover:bg-dark-border/80 transition-colors">
                    Create Alert
                  </button>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Facility context circles */}
        {layers.circles && filteredMarkers.map((m) => (
          <Circle
            key={`circle-${m.id}`}
            center={m.position}
            radius={5000}
            pathOptions={{
              color: riskColors[m.riskLevel],
              fillColor: riskColors[m.riskLevel],
              fillOpacity: 0.15,
              weight: 1,
            }}
          />
        ))}
      </MapContainer>

      {/* Facility quick-toggle bar */}
      <FacilityToggleBar
        layers={layers}
        setLayers={setLayers}
        anomalyMode={anomalyMode}
        setAnomalyMode={setAnomalyMode}
      />

      {/* Controls */}
      <MapControls
        filters={filters}
        setFilters={setFilters}
        layers={layers}
        setLayers={setLayers}
        anomalyMode={anomalyMode}
        setAnomalyMode={setAnomalyMode}
        onRefresh={handleRefresh}
        onLocateMe={getUserLocation}
        isLocating={isLocating}
        isLoadingHeatmap={isLoadingHeatmap}
      />

      {/* Legend */}
      <HeatmapLegend stats={heatmapStats} />

      {/* Heatmap error toast */}
      <AnimatePresence>
        {heatmapError && (
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
            className="absolute bottom-20 left-1/2 -translate-x-1/2 z-[2000] glass-card px-5 py-3 flex items-center gap-3"
          >
            <AlertTriangle className="w-5 h-5 text-warning-yellow flex-shrink-0" />
            <span className="text-white text-sm">{heatmapError}</span>
            <button onClick={() => setHeatmapError(null)} className="text-gray-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Location error toast */}
      <AnimatePresence>
        {locationError && (
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 z-[2000] glass-card px-5 py-3 flex items-center gap-3"
          >
            <AlertTriangle className="w-5 h-5 text-warning-yellow flex-shrink-0" />
            <span className="text-white text-sm">{locationError}</span>
            <button onClick={() => setLocationError(null)} className="text-gray-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading overlay */}
      {(isLoading || isLoadingHeatmap) && (
        <div className="absolute inset-0 bg-dark-bg/50 z-[2000] flex items-center justify-center">
          <div className="glass-card p-6 flex items-center gap-3">
            <RefreshCw className="w-5 h-5 text-accent-green animate-spin" />
            <span className="text-white">
              {isLoadingHeatmap ? 'Loading satellite heatmap...' : 'Refreshing data...'}
            </span>
          </div>
        </div>
      )}

      {/* Selected marker detail panel */}
      <AnimatePresence>
        {selectedMarker && (
          <motion.div
            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
            className="absolute bottom-4 right-4 z-[1000] glass-card p-4 w-80"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-semibold text-white">{selectedMarker.name}</h3>
                <p className="text-xs text-gray-500 mt-1">
                  {selectedMarker.subLabel || 'Facility'}
                </p>
              </div>
              <button onClick={() => setSelectedMarker(null)}>
                <X className="w-5 h-5 text-gray-400 hover:text-white" />
              </button>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Risk Level</span>
                <StatusBadge status={selectedMarker.riskLevel} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Operator</span>
                <span className="text-sm text-white font-medium">{selectedMarker.operator || 'Unknown'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Status</span>
                <span className="text-sm text-white">{selectedMarker.status || 'active'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Coordinates</span>
                <span className="text-sm text-white font-mono">
                  {selectedMarker.position[0].toFixed(4)}, {selectedMarker.position[1].toFixed(4)}
                </span>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t border-dark-border">
              <button className="w-full btn-primary text-sm py-2">View Full Details</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default LiveMap
