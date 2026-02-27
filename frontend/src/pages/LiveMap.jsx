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
} from 'lucide-react'
import { geeService, geojsonService, detectedHotspotsService } from '../services/api'
import { StatusBadge } from '../components/ui/AlertCard'
import HeatmapLayer from '../components/map/HeatmapLayer'

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
        width:14px;height:14px;border-radius:50%;
        background:${color};border:2px solid #fff;
        box-shadow:0 0 8px ${color}88;
      "></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    popupAnchor: [0, -10],
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
      attribution="Copernicus Sentinel-5P / GEE"
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
    { key: 'geeTiles', label: 'GEE Tile Overlay', desc: 'Satellite raster tiles', icon: Layers },
    { key: 'markers', label: 'Hotspot Markers', desc: 'Detected point locations', icon: MapPin },
    { key: 'circles', label: 'Emission Circles', desc: 'Emission intensity rings', icon: Activity },
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

// ─── Hotspot Quick-Toggle Bar ───────────────────────────────────────────

const HotspotToggleBar = ({ layers, setLayers }) => {
  const toggle = (key) => setLayers((prev) => ({ ...prev, [key]: !prev[key] }))

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
      activeLabel: 'Hotspots ON',
      inactiveLabel: 'Hotspots OFF',
      activeStyle: 'bg-amber-600 text-white border-amber-500 shadow-lg shadow-amber-900/40',
      inactiveStyle: 'bg-dark-card/80 text-gray-400 border-dark-border hover:border-amber-500/50 hover:text-amber-400',
      dot: 'bg-amber-400',
      icon: MapPin,
    },
    {
      key: 'circles',
      activeLabel: 'Rings ON',
      inactiveLabel: 'Rings OFF',
      activeStyle: 'bg-orange-600 text-white border-orange-500 shadow-lg shadow-orange-900/40',
      inactiveStyle: 'bg-dark-card/80 text-gray-400 border-dark-border hover:border-orange-500/50 hover:text-orange-400',
      dot: 'bg-orange-400',
      icon: Activity,
    },
  ]

  return (
    <div className="absolute top-[4.5rem] left-1/2 -translate-x-1/2 z-[1000] flex gap-2">
      {btns.map(({ key, activeLabel, inactiveLabel, activeStyle, inactiveStyle, dot, icon: Icon }) => {
        const on = layers[key]
        return (
          <button
            key={key}
            onClick={() => toggle(key)}
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
    </div>
  )
}

// ─── Main LiveMap component ──────────────────────────────────────────────

const LiveMap = () => {
  const [selectedMarker, setSelectedMarker] = useState(null)
  const [filters, setFilters] = useState({
    riskLevels: ['Critical', 'High', 'Medium', 'Low'],
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

  // User location
  const [userLocation, setUserLocation] = useState(null)
  const [locationError, setLocationError] = useState(null)
  const [isLocating, setIsLocating] = useState(false)
  const [flyToTrigger, setFlyToTrigger] = useState(0)

  // ── Fetch heatmap data from GEE ─────────────────────────────────────

  const fetchHeatmapData = useCallback(async () => {
    setIsLoadingHeatmap(true)
    setHeatmapError(null)

    // Fire both requests in parallel
    const [heatmapRes, tileRes] = await Promise.allSettled([
      geeService.getCH4Heatmap(30, 1000, 20000),
      geeService.getCH4Tiles(30),
    ])

    if (heatmapRes.status === 'fulfilled' && heatmapRes.value?.points?.length) {
      setHeatmapPoints(heatmapRes.value.points)
      setHeatmapStats(heatmapRes.value.stats)
    } else {
      const err = heatmapRes.status === 'rejected' ? heatmapRes.reason : null
      console.warn('Heatmap points unavailable:', err?.message || 'empty')
      setHeatmapError('GEE heatmap data unavailable \u2013 showing markers only')
    }

    if (tileRes.status === 'fulfilled' && tileRes.value?.tile_url) {
      setGeeTileUrl(tileRes.value.tile_url)
    } else {
      console.warn('GEE tile URL unavailable')
    }

    setIsLoadingHeatmap(false)
  }, [])

  // ── Fetch marker data from backend ──────────────────────────────────

  const fetchMarkerData = useCallback(async () => {
    setIsLoading(true)
    try {
      const [facilitiesGeo, hotspotsGeo] = await Promise.all([
        geojsonService.getFacilities().catch(() => null),
        geojsonService.getHotspots().catch(() => null),
      ])

      const markers = []
      let id = 1

      if (facilitiesGeo?.features) {
        for (const f of facilitiesGeo.features) {
          const c = f.geometry?.coordinates
          if (c) markers.push({
            id: id++,
            position: [c[1], c[0]],
            name: f.properties?.name || 'Unknown Facility',
            emission: 0,
            riskLevel: 'Medium',
            lastDetected: 'N/A',
            type: 'leak',
          })
        }
      }

      if (hotspotsGeo?.features) {
        for (const f of hotspotsGeo.features) {
          const c = f.geometry?.coordinates
          if (!c) continue
          const sev = f.properties?.severity || 'medium'
          const riskMap = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' }
          markers.push({
            id: id++,
            position: [c[1], c[0]],
            name: f.properties?.label || `Hotspot #${f.properties?.system_index || id}`,
            emission: f.properties?.count || 0,
            riskLevel: riskMap[sev] || 'Medium',
            lastDetected: 'Sentinel-5P',
            type: sev === 'critical' || sev === 'high' ? 'super-emitter' : 'leak',
          })
        }
      }

      if (markers.length === 0) {
        const hotspots = await detectedHotspotsService.getAll({ ordering: '-anomaly_score' })
        const list = Array.isArray(hotspots) ? hotspots : []
        list.forEach((h, i) => {
          if (h.latitude && h.longitude) {
            const sev = (h.severity || 'medium').toLowerCase()
            const riskMap = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' }
            markers.push({
              id: i + 1,
              position: [h.latitude, h.longitude],
              name: h.hotspot_id || `Hotspot ${i + 1}`,
              emission: h.ch4_count || 0,
              riskLevel: riskMap[sev] || 'Medium',
              lastDetected: h.detected_at || 'N/A',
              type: sev === 'critical' || sev === 'high' ? 'super-emitter' : 'leak',
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
            Real-time methane heatmap from Sentinel-5P TROPOMI
            {heatmapStats?.count ? ` \u2022 ${heatmapStats.count.toLocaleString()} samples` : ''}
            {filteredMarkers.length > 0 ? ` \u2022 ${filteredMarkers.length} markers` : ''}
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
              blur: 15,
              maxZoom: 10,
              max: 1.0,
              minOpacity: 0.35,
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

        {/* Hotspot markers */}
        {layers.markers && filteredMarkers.map((m) => (
          <Marker key={m.id} position={m.position} icon={markerIcons[m.riskLevel]}
            eventHandlers={{ click: () => setSelectedMarker(m) }}>
            <Popup className="custom-popup">
              <div className="min-w-[250px]">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-white text-sm">{m.name}</h3>
                  <StatusBadge status={m.riskLevel} />
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-gray-400">
                    <MapPin className="w-4 h-4" />
                    <span>{m.position[0].toFixed(4)}, {m.position[1].toFixed(4)}</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <Activity className="w-4 h-4" />
                    <span><span className="text-white font-medium">{m.emission}</span> kg/hr</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <Clock className="w-4 h-4" />
                    <span>Last detected: {m.lastDetected}</span>
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

        {/* Emission intensity circles */}
        {layers.circles && filteredMarkers.map((m) => (
          <Circle
            key={`circle-${m.id}`}
            center={m.position}
            radius={m.emission * 50}
            pathOptions={{
              color: riskColors[m.riskLevel],
              fillColor: riskColors[m.riskLevel],
              fillOpacity: 0.15,
              weight: 1,
            }}
          />
        ))}
      </MapContainer>

      {/* Hotspot quick-toggle bar */}
      <HotspotToggleBar layers={layers} setLayers={setLayers} />

      {/* Controls */}
      <MapControls
        filters={filters}
        setFilters={setFilters}
        layers={layers}
        setLayers={setLayers}
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
              {isLoadingHeatmap ? 'Loading heatmap from Google Earth Engine...' : 'Refreshing data...'}
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
                  {selectedMarker.type === 'super-emitter' ? 'Super Emitter' : 'Standard Leak'}
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
                <span className="text-sm text-gray-400">Emission Rate</span>
                <span className="text-sm text-white font-medium">{selectedMarker.emission} kg/hr</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Last Detected</span>
                <span className="text-sm text-white">{selectedMarker.lastDetected}</span>
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
