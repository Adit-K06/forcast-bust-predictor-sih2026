import { useState } from 'react'
import Header from './components/Header'
import ForecastControls from './components/ForecastControls'
import MapView from './components/MapView'
import RegionPanel from './components/RegionPanel'
import ConfidenceLegend from './components/ConfidenceLegend'

const DEFAULT_DATE = '2026-08-28'

function App() {
  const [forecastDate, setForecastDate] = useState(DEFAULT_DATE)
  const [leadDay, setLeadDay] = useState(5)
  const [region, setRegion] = useState('all-india')

  return (
    <div className="app-shell">
      <Header />

      <ForecastControls
        forecastDate={forecastDate}
        onForecastDateChange={setForecastDate}
        leadDay={leadDay}
        onLeadDayChange={setLeadDay}
        region={region}
        onRegionChange={setRegion}
      />

      <main className="dashboard-main">
        <section className="map-panel" aria-label="Forecast map">
          <MapView />
        </section>
        <aside className="intel-panel" aria-label="Region intelligence">
          <RegionPanel
            forecastDate={forecastDate}
            leadDay={leadDay}
            region={region}
          />
        </aside>
      </main>

      <footer className="status-bar">
        <ConfidenceLegend />
        <div className="status-text">
          <span className="status-dot" aria-hidden="true" />
          Prototype environment — no live forecast data connected
        </div>
      </footer>
    </div>
  )
}

export default App