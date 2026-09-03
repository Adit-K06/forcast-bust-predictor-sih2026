import { useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'

const INDIA_CENTER = [22.9734, 78.6569]
const INITIAL_ZOOM = 5

// Maps region slug to fill colour based on bust probability
function getBustColour(bustProbability) {
  if (bustProbability == null) return { fillColor: '#1c2230', fillOpacity: 0.3 }
  if (bustProbability < 0.30) return { fillColor: '#2ea043', fillOpacity: 0.45 }
  if (bustProbability < 0.60) return { fillColor: '#d29922', fillOpacity: 0.45 }
  return { fillColor: '#f85149', fillOpacity: 0.50 }
}

// GeoJSON state name -> backend region slug mapping
const STATE_TO_SLUG = {
  'Karnataka': 'coastal-karnataka',
  'Goa': 'konkan-goa',
  'Maharashtra': 'vidarbha',
  'Rajasthan': 'west-rajasthan',
  'West Bengal': 'gangetic-west-bengal',
  'Bihar': 'gangetic-west-bengal',
  'Jharkhand': 'gangetic-west-bengal',
  'Uttar Pradesh': 'gangetic-west-bengal',
}

function MapView({ onStateClick, mapData, selectedRegion }) {
  const [geojson, setGeojson] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const onStateClickRef = useRef(onStateClick)
  const mapDataRef = useRef(mapData)
  const selectedRef = useRef(selectedRegion)

  useEffect(() => { onStateClickRef.current = onStateClick }, [onStateClick])
  useEffect(() => { mapDataRef.current = mapData }, [mapData])
  useEffect(() => { selectedRef.current = selectedRegion }, [selectedRegion])

  useEffect(() => {
    let cancelled = false
    const url = new URL('../data/india_subdivisions.geojson', import.meta.url)
    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error(`Failed to load boundaries (${res.status})`)
        return res.json()
      })
      .then(data => { if (!cancelled) setGeojson(data) })
      .catch(err => { if (!cancelled) setLoadError(err.message) })
    return () => { cancelled = true }
  }, [])

  // Build slug -> bust_probability map from mapData
  function getRegionBustMap() {
    if (!mapDataRef.current?.regions) return {}
    const m = {}
    for (const r of mapDataRef.current.regions) m[r.region] = r.bust_probability
    return m
  }

  function getStateStyle(feature) {
    const stateName = feature.properties?.NAME_1
    const slug = STATE_TO_SLUG[stateName]
    const bustMap = getRegionBustMap()
    const bustProb = slug ? bustMap[slug] : null
    const colour = getBustColour(bustProb)
    const isSelected = slug && slug === selectedRef.current

    return {
      ...colour,
      color: isSelected ? '#388bfd' : 'rgba(255,255,255,0.15)',
      weight: isSelected ? 2 : 0.7,
      interactive: true,
    }
  }

  function onEachFeature(feature, layer) {
    const stateName = feature.properties?.NAME_1
    const slug = STATE_TO_SLUG[stateName]

    layer.on('mouseover', e => {
      e.target.setStyle({
        fillOpacity: 0.70,
        color: '#58a6ff',
        weight: 1.5,
      })
      e.target.bringToFront()
    })

    layer.on('mouseout', e => {
      e.target.setStyle(getStateStyle(feature))
    })

    layer.on('click', e => {
      if (e.originalEvent) e.originalEvent.stopPropagation()
      onStateClickRef.current?.(stateName)
    })

    if (stateName) {
      const bustMap = getRegionBustMap()
      const bust = slug ? bustMap[slug] : null
      const bustStr = bust != null ? ` — ${Math.round(bust * 100)}% bust risk` : ' (no data)'
      layer.bindTooltip(
        `<strong>${stateName}</strong>${bustStr}`,
        { sticky: true, className: 'state-tooltip' }
      )
    }
  }

  return (
    <div className="map-container">
      <MapContainer
        center={INDIA_CENTER}
        zoom={INITIAL_ZOOM}
        minZoom={4}
        maxZoom={10}
        scrollWheelZoom
        className="leaflet-instance"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {geojson && (
          <GeoJSON
            key={`india-${mapData ? JSON.stringify(mapData).slice(0, 50) : 'base'}-${selectedRegion}`}
            data={geojson}
            style={getStateStyle}
            onEachFeature={onEachFeature}
          />
        )}
      </MapContainer>

      {!geojson && !loadError && (
        <div className="map-overlay-card">Loading regional boundaries…</div>
      )}
      {loadError && (
        <div className="map-overlay-card" style={{ color: 'var(--risk-high)' }}>
          ⚠ Unable to load boundaries
        </div>
      )}
      {geojson && (
        <div className="map-overlay-card">
          Click a highlighted state · Colour = bust risk level
        </div>
      )}
    </div>
  )
}

export default MapView