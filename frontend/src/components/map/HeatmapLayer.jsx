/**
 * HeatmapLayer – react-leaflet v5 wrapper for leaflet.heat
 *
 * Usage:
 *   <HeatmapLayer
 *     points={[[lat, lng, intensity], ...]}
 *     options={{ radius: 25, blur: 15, maxZoom: 10 }}
 *   />
 *
 * Must be used inside a <MapContainer>.
 */

import { useEffect, useRef, useMemo } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.heat'

const HeatmapLayer = ({
  points = [],
  options = {},
}) => {
  const map = useMap()
  const heatLayerRef = useRef(null)

  // Default options – red-orange heat theme:
  // low intensity → light peach/orange → deep red at peak
  const defaultOptions = {
    radius: 30,
    blur: 20,
    maxZoom: 10,
    max: 1.0,
    minOpacity: 0.3,
    gradient: {
      0.0:  '#fff3e0',   // very light warm white
      0.15: '#ffcc80',   // light peach-orange
      0.3:  '#ffa040',   // orange
      0.5:  '#f36f21',   // deep orange
      0.7:  '#e53935',   // red
      0.85: '#b71c1c',   // dark red
      1.0:  '#7f0000',   // deep crimson
    },
  }

  // Memoize merged options so we only re-create the heat layer when actual
  // option values change (not on every parent render).
  const mergedOptions = useMemo(
    () => ({ ...defaultOptions, ...options }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(options)],
  )

  useEffect(() => {
    if (!map) return

    // Remove previous heat layer
    if (heatLayerRef.current) {
      map.removeLayer(heatLayerRef.current)
      heatLayerRef.current = null
    }

    if (points.length === 0) return

    // L.heatLayer expects [[lat, lng, intensity?], ...]
    const layer = L.heatLayer(points, mergedOptions)
    layer.addTo(map)
    heatLayerRef.current = layer

    return () => {
      if (heatLayerRef.current) {
        map.removeLayer(heatLayerRef.current)
        heatLayerRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, points, mergedOptions])

  return null
}

export default HeatmapLayer
