import { MapContainer, TileLayer } from 'react-leaflet'

const INDIA_CENTER = [22.9734, 78.6569]
const INITIAL_ZOOM = 5

function MapView() {
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
      </MapContainer>

      <div className="map-note">Regional risk layer will be connected next.</div>
    </div>
  )
}

export default MapView