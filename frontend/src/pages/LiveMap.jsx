import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet'
import L from 'leaflet'
import {
  Layers,
  Filter,
  RefreshCw,
  Maximize2,
  MapPin,
  AlertTriangle,
  Clock,
  Activity,
  X,
  Navigation2,
  Crosshair,
} from 'lucide-react'
import { mapMarkers } from '../data/mockData'
import { StatusBadge } from '../components/ui/AlertCard'

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

// Custom marker icons
const createCustomIcon = (color) => {
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        width: 24px;
        height: 24px;
        background: ${color};
        border: 3px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        position: relative;
      ">
        <div style="
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 8px;
          height: 8px;
          background: white;
          border-radius: 50%;
        "></div>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  })
}

const markerIcons = {
  Critical: createCustomIcon('#ef4444'),
  High: createCustomIcon('#f97316'),
  Medium: createCustomIcon('#eab308'),
  Low: createCustomIcon('#22c55e'),
}

// User location marker icon (blue with pulse animation)
const userLocationIcon = L.divIcon({
  className: 'user-location-marker',
  html: `
    <div style="position: relative; width: 24px; height: 24px;">
      <div style="
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 40px;
        height: 40px;
        background: rgba(59, 130, 246, 0.3);
        border-radius: 50%;
        animation: pulse 2s ease-out infinite;
      "></div>
      <div style="
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 16px;
        height: 16px;
        background: #3b82f6;
        border: 3px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 10px rgba(59, 130, 246, 0.5);
      "></div>
    </div>
    <style>
      @keyframes pulse {
        0% { transform: translate(-50%, -50%) scale(0.5); opacity: 1; }
        100% { transform: translate(-50%, -50%) scale(2); opacity: 0; }
      }
    </style>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
  popupAnchor: [0, -12],
})

/**
 * Component to fly map to user's location
 */
const FlyToLocation = ({ position, trigger }) => {
  const map = useMap()
  
  useEffect(() => {
    if (position && trigger) {
      map.flyTo(position, 14, { duration: 1.5 })
    }
  }, [position, trigger, map])
  
  return null
}

/**
 * Map Controls Component
 */
const MapControls = ({ filters, setFilters, onRefresh, onLocateMe, isLocating }) => {
  const [showFilters, setShowFilters] = useState(false)

  return (
    <div className="absolute top-4 right-4 z-[1000] flex flex-col gap-2">
      {/* Control buttons */}
      <div className="glass-card p-2 flex flex-col gap-2">
        <button
          onClick={onLocateMe}
          disabled={isLocating}
          className={`p-2 rounded-lg transition-colors ${
            isLocating ? 'bg-info-blue/20 text-info-blue' : 'hover:bg-dark-border text-gray-400 hover:text-white'
          }`}
          title="My Location"
        >
          <Crosshair className={`w-5 h-5 ${isLocating ? 'animate-pulse' : ''}`} />
        </button>
        <button
          onClick={onRefresh}
          className="p-2 hover:bg-dark-border rounded-lg transition-colors"
          title="Refresh Data"
        >
          <RefreshCw className="w-5 h-5 text-gray-400 hover:text-white" />
        </button>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`p-2 rounded-lg transition-colors ${
            showFilters ? 'bg-accent-green/20 text-accent-green' : 'hover:bg-dark-border text-gray-400 hover:text-white'
          }`}
          title="Filters"
        >
          <Filter className="w-5 h-5" />
        </button>
        <button
          className="p-2 hover:bg-dark-border rounded-lg transition-colors"
          title="Layers"
        >
          <Layers className="w-5 h-5 text-gray-400 hover:text-white" />
        </button>
        <button
          className="p-2 hover:bg-dark-border rounded-lg transition-colors"
          title="Fullscreen"
        >
          <Maximize2 className="w-5 h-5 text-gray-400 hover:text-white" />
        </button>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="glass-card p-4 w-64"
        >
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold text-white">Filters</h4>
            <button onClick={() => setShowFilters(false)}>
              <X className="w-4 h-4 text-gray-400" />
            </button>
          </div>

          <div className="space-y-4">
            {/* Risk Level */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">Risk Level</label>
              <div className="space-y-2">
                {['Critical', 'High', 'Medium', 'Low'].map((level) => (
                  <label key={level} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.riskLevels.includes(level)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFilters({
                            ...filters,
                            riskLevels: [...filters.riskLevels, level],
                          })
                        } else {
                          setFilters({
                            ...filters,
                            riskLevels: filters.riskLevels.filter((l) => l !== level),
                          })
                        }
                      }}
                      className="w-4 h-4 rounded border-dark-border bg-dark-bg text-accent-green focus:ring-accent-green"
                    />
                    <span className="text-sm text-gray-300">{level}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Type Filter */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">Type</label>
              <div className="space-y-2">
                {['super-emitter', 'leak'].map((type) => (
                  <label key={type} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.types.includes(type)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFilters({
                            ...filters,
                            types: [...filters.types, type],
                          })
                        } else {
                          setFilters({
                            ...filters,
                            types: filters.types.filter((t) => t !== type),
                          })
                        }
                      }}
                      className="w-4 h-4 rounded border-dark-border bg-dark-bg text-accent-green focus:ring-accent-green"
                    />
                    <span className="text-sm text-gray-300 capitalize">{type.replace('-', ' ')}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

/**
 * Map Legend Component
 */
const MapLegend = () => {
  const legendItems = [
    { color: '#ef4444', label: 'Critical' },
    { color: '#f97316', label: 'High' },
    { color: '#eab308', label: 'Medium' },
    { color: '#22c55e', label: 'Low' },
  ]

  return (
    <div className="absolute bottom-4 left-4 z-[1000] glass-card p-4">
      <h4 className="text-sm font-semibold text-white mb-3">Risk Level</h4>
      <div className="space-y-2">
        {legendItems.map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            <div
              className="w-4 h-4 rounded-full border-2 border-white"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-xs text-gray-400">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * Live Map Page Component
 * Interactive map with methane plume markers and heatmap overlay
 */
const LiveMap = () => {
  const [selectedMarker, setSelectedMarker] = useState(null)
  const [filters, setFilters] = useState({
    riskLevels: ['Critical', 'High', 'Medium', 'Low'],
    types: ['super-emitter', 'leak'],
  })
  const [isLoading, setIsLoading] = useState(false)
  
  // User location states
  const [userLocation, setUserLocation] = useState(null)
  const [locationError, setLocationError] = useState(null)
  const [isLocating, setIsLocating] = useState(false)
  const [flyToTrigger, setFlyToTrigger] = useState(0)
  const [watchId, setWatchId] = useState(null)

  // Get user's current location
  const getUserLocation = () => {
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported by your browser')
      return
    }

    setIsLocating(true)
    setLocationError(null)

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords
        setUserLocation({ lat: latitude, lng: longitude, accuracy })
        setFlyToTrigger((prev) => prev + 1)
        setIsLocating(false)
      },
      (error) => {
        setIsLocating(false)
        switch (error.code) {
          case error.PERMISSION_DENIED:
            setLocationError('Location permission denied. Please enable in browser settings.')
            break
          case error.POSITION_UNAVAILABLE:
            setLocationError('Location information unavailable.')
            break
          case error.TIMEOUT:
            setLocationError('Location request timed out.')
            break
          default:
            setLocationError('An unknown error occurred.')
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      }
    )
  }

  // Watch user's location for real-time updates
  useEffect(() => {
    if (navigator.geolocation) {
      const id = navigator.geolocation.watchPosition(
        (position) => {
          const { latitude, longitude, accuracy } = position.coords
          setUserLocation({ lat: latitude, lng: longitude, accuracy })
        },
        () => {}, // Silently ignore watch errors
        {
          enableHighAccuracy: true,
          timeout: 30000,
          maximumAge: 10000,
        }
      )
      setWatchId(id)

      return () => {
        if (id) navigator.geolocation.clearWatch(id)
      }
    }
  }, [])

  // Filter markers based on selected filters
  const filteredMarkers = mapMarkers.filter(
    (marker) =>
      filters.riskLevels.includes(marker.riskLevel) &&
      filters.types.includes(marker.type)
  )

  // Refresh data simulation
  const handleRefresh = () => {
    setIsLoading(true)
    setTimeout(() => setIsLoading(false), 1000)
  }

  // Center of US for default view
  const defaultCenter = [39.8283, -98.5795]
  const defaultZoom = 4

  return (
    <div className="h-[calc(100vh-7rem)] relative">
      {/* Page Header */}
      <div className="absolute top-0 left-0 right-0 z-[1000] p-4 bg-gradient-to-b from-dark-bg to-transparent pointer-events-none">
        <div className="pointer-events-auto inline-block">
          <h1 className="text-2xl font-bold text-white">Live Detection Map</h1>
          <p className="text-gray-400 text-sm mt-1">
            Real-time methane emission monitoring • {filteredMarkers.length} active markers
          </p>
        </div>
      </div>

      {/* Map Container */}
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        className="w-full h-full rounded-xl overflow-hidden"
        style={{ background: '#0f172a' }}
      >
        {/* Dark theme tile layer */}
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* Fly to user location helper */}
        <FlyToLocation position={userLocation ? [userLocation.lat, userLocation.lng] : null} trigger={flyToTrigger} />

        {/* User location marker */}
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
                    {userLocation.accuracy && (
                      <p>Accuracy: ±{Math.round(userLocation.accuracy)}m</p>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
            {/* Accuracy circle */}
            <Circle
              center={[userLocation.lat, userLocation.lng]}
              radius={userLocation.accuracy || 100}
              pathOptions={{
                color: '#3b82f6',
                fillColor: '#3b82f6',
                fillOpacity: 0.1,
                weight: 1,
                dashArray: '5, 5',
              }}
            />
          </>
        )}

        {/* Markers */}
        {filteredMarkers.map((marker) => (
          <Marker
            key={marker.id}
            position={marker.position}
            icon={markerIcons[marker.riskLevel]}
            eventHandlers={{
              click: () => setSelectedMarker(marker),
            }}
          >
            <Popup className="custom-popup">
              <div className="min-w-[250px]">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-white text-sm">{marker.name}</h3>
                  <StatusBadge status={marker.riskLevel} />
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-gray-400">
                    <MapPin className="w-4 h-4" />
                    <span>
                      {marker.position[0].toFixed(4)}, {marker.position[1].toFixed(4)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <Activity className="w-4 h-4" />
                    <span>
                      <span className="text-white font-medium">{marker.emission}</span> kg/hr estimated emission
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <Clock className="w-4 h-4" />
                    <span>Last detected: {marker.lastDetected}</span>
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

        {/* Heat circles for emission intensity */}
        {filteredMarkers.map((marker) => (
          <Circle
            key={`circle-${marker.id}`}
            center={marker.position}
            radius={marker.emission * 50}
            pathOptions={{
              color: marker.riskLevel === 'Critical' ? '#ef4444' :
                     marker.riskLevel === 'High' ? '#f97316' :
                     marker.riskLevel === 'Medium' ? '#eab308' : '#22c55e',
              fillColor: marker.riskLevel === 'Critical' ? '#ef4444' :
                         marker.riskLevel === 'High' ? '#f97316' :
                         marker.riskLevel === 'Medium' ? '#eab308' : '#22c55e',
              fillOpacity: 0.15,
              weight: 1,
            }}
          />
        ))}
      </MapContainer>

      {/* Map Controls */}
      <MapControls
        filters={filters}
        setFilters={setFilters}
        onRefresh={handleRefresh}
        onLocateMe={getUserLocation}
        isLocating={isLocating}
      />

      {/* Legend */}
      <MapLegend />

      {/* Location Error Toast */}
      {locationError && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-[2000] glass-card p-4 flex items-center gap-3"
        >
          <AlertTriangle className="w-5 h-5 text-warning-yellow" />
          <span className="text-white text-sm">{locationError}</span>
          <button 
            onClick={() => setLocationError(null)}
            className="text-gray-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </motion.div>
      )}

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-dark-bg/50 z-[2000] flex items-center justify-center">
          <div className="glass-card p-6 flex items-center gap-3">
            <RefreshCw className="w-5 h-5 text-accent-green animate-spin" />
            <span className="text-white">Refreshing data...</span>
          </div>
        </div>
      )}

      {/* Selected Marker Detail Panel */}
      {selectedMarker && (
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
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
            <button className="w-full btn-primary text-sm py-2">
              View Full Details
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default LiveMap
