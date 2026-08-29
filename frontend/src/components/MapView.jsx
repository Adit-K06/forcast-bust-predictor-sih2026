import { useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'

const INDIA_CENTER = [22.9734, 78.6569]
const INITIAL_ZOOM = 5

const BASE_STYLE = {
  fillColor: '#2e4a66',
  fillOpacity: 0.35,
  color: '#4c8fd9',
  weight: 1,
  interactive: true,
}

const HOVER_STYLE = {
  fillColor: '#2e4a66',
  fillOpacity: 0.55,
  color: '#4c8fd9',
  weight: 2,
  interactive: true,
}

function MapView({ onStateClick }) {
  const [geojson, setGeojson] = useState(null)
  const [loadError, setLoadError] = useState(null)

  // Keep a live ref to the latest onStateClick. onEachFeature only runs once,
  // when the GeoJSON layer is created, so the click handler must read the
  // callback through a ref rather than closing over the prop directly —
  // otherwise a stale or missing callback at layer-creation time would
  // silently no-op on every click.
  const onStateClickRef = useRef(onStateClick)
  useEffect(() => {
    onStateClickRef.current = onStateClick
  }, [onStateClick])

  useEffect(() => {
    let cancelled = false
    const url = new URL('../data/india_subdivisions.geojson', import.meta.url)

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load boundaries (${res.status})`)
        return res.json()
      })
      .then((data) => {
        if (!cancelled) setGeojson(data)
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err.message)
      })

    return () => {
      cancelled = true
    }
  }, [])

  function onEachFeature(feature, layer) {
    
    const stateName = feature.properties?.NAME_1

    layer.on('mouseover', (e) => {
      e.target.setStyle(HOVER_STYLE)
      e.target.bringToFront()
    })

    layer.on('mouseout', (e) => {
      e.target.setStyle(BASE_STYLE)
    })

    layer.on('click', (e) => {
      // Prevent the click from also firing on the underlying map/tile layer.
      if (e.originalEvent) {
        e.originalEvent.stopPropagation()
      }
      console.log('STATE CLICKED:', stateName)
onStateClickRef.current?.(stateName)
    })

    if (stateName) {
      layer.bindTooltip(stateName, { sticky: true, className: 'state-tooltip' })
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
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {geojson && (
          <GeoJSON
            key="india-state-boundaries"
            data={geojson}
            style={() => BASE_STYLE}
            onEachFeature={onEachFeature}
          />
        )}
      </MapContainer>

      {!geojson && !loadError && (
        <div className="map-note">Loading regional boundaries…</div>
      )}
      {loadError && (
        <div className="map-note map-note-error">Unable to load regional boundaries.</div>
      )}
      {geojson && (
        <div className="map-note">
          Click a state to check forecast data availability.
        </div>
      )}
    </div>
  )
}

export default MapView