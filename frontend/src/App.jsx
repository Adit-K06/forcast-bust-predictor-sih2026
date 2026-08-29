import { useState, useEffect } from 'react'
import Header from './components/Header'
import ForecastControls from './components/ForecastControls'
import MapView from './components/MapView'
import RegionPanel from './components/RegionPanel'
import ConfidenceLegend from './components/ConfidenceLegend'
import { getForecastConfidence } from './api/forecastApi'
import { getBackendSlugForState } from './data/regionSlugMap'

const DEFAULT_DATE = '2026-08-28'

function App() {
  const [forecastDate, setForecastDate] = useState(DEFAULT_DATE)
  const [leadDay, setLeadDay] = useState(5)
  const [region, setRegion] = useState('all-india')
  const [apiState, setApiState] = useState({ status: 'idle', data: null, error: null })
  const [mapNotice, setMapNotice] = useState(null)

  useEffect(() => {
    let cancelled = false
    setApiState({ status: 'loading', data: null, error: null })

    getForecastConfidence(region, forecastDate, leadDay)
      .then((data) => {
        if (!cancelled) setApiState({ status: 'success', data, error: null })
      })
      .catch((err) => {
        if (!cancelled) setApiState({ status: 'error', data: null, error: err.message })
      })

    return () => {
      cancelled = true
    }
  }, [region, forecastDate, leadDay])

  function handleStateClick(stateName) {
    const slug = getBackendSlugForState(stateName)
    if (slug) {
      setMapNotice(null)
      setRegion(slug)
    } else {
      setMapNotice(stateName)
    }
  }

  function handleRegionChange(value) {
    setMapNotice(null)
    setRegion(value)
  }

  return (
    <div className="app-shell">
      <Header />

      <ForecastControls
        forecastDate={forecastDate}
        onForecastDateChange={setForecastDate}
        leadDay={leadDay}
        onLeadDayChange={setLeadDay}
        region={region}
        onRegionChange={handleRegionChange}
      />

      <main className="dashboard-main">
        <section className="map-panel" aria-label="Forecast map">
          <MapView onStateClick={handleStateClick} />
        </section>
        <aside className="intel-panel" aria-label="Region intelligence">
          <RegionPanel
            region={region}
            forecastDate={forecastDate}
            leadDay={leadDay}
            apiState={apiState}
            mapNotice={mapNotice}
          />
        </aside>
      </main>

      <footer className="status-bar">
        <ConfidenceLegend />
        <div className="status-text">
          <span className="status-dot" aria-hidden="true" />
          Prototype environment — mock data from P5's backend
        </div>
      </footer>
    </div>
  )
}

export default App