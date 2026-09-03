import { useState, useEffect, useCallback } from 'react'
import Header from './components/Header'
import ForecastControls from './components/ForecastControls'
import MapView from './components/MapView'
import RegionPanel from './components/RegionPanel'
import OutlookChart from './components/OutlookChart'
import BustEventsPanel from './components/BustEventsPanel'
import ModelInfoBadge from './components/ModelInfoBadge'
import { getForecastConfidence, get10DayOutlook, getConfidenceMap, getBustEvents, getRegions } from './api/forecastApi'
import { getBackendSlugForState } from './data/regionSlugMap'

const DEFAULT_DATE = new Date().toISOString().slice(0, 10)

function App() {
  const [forecastDate, setForecastDate] = useState('2023-08-15')
  const [leadDay, setLeadDay] = useState(1)
  const [region, setRegion] = useState('coastal-karnataka')
  const [activeTab, setActiveTab] = useState('forecast') // 'forecast' | 'events' | 'model'

  const [apiState, setApiState] = useState({ status: 'idle', data: null, error: null })
  const [outlookState, setOutlookState] = useState({ status: 'idle', data: null })
  const [mapData, setMapData] = useState(null)
  const [bustEvents, setBustEvents] = useState([])
  const [regions, setRegions] = useState([])
  const [mapNotice, setMapNotice] = useState(null)

  // Load static data
  useEffect(() => {
    getBustEvents().then(setBustEvents).catch(() => {})
    getRegions().then(setRegions).catch(() => {})
  }, [])

  // Fetch forecast confidence
  useEffect(() => {
    let cancelled = false
    setApiState({ status: 'loading', data: null, error: null })
    getForecastConfidence(region, forecastDate, leadDay)
      .then(data => { if (!cancelled) setApiState({ status: 'success', data, error: null }) })
      .catch(err => { if (!cancelled) setApiState({ status: 'error', data: null, error: err.message }) })
    return () => { cancelled = true }
  }, [region, forecastDate, leadDay])

  // Fetch 10-day outlook
  useEffect(() => {
    let cancelled = false
    setOutlookState({ status: 'loading', data: null })
    get10DayOutlook(region, forecastDate)
      .then(data => { if (!cancelled) setOutlookState({ status: 'success', data }) })
      .catch(() => { if (!cancelled) setOutlookState({ status: 'error', data: null }) })
    return () => { cancelled = true }
  }, [region, forecastDate])

  // Fetch map confidence data
  useEffect(() => {
    let cancelled = false
    getConfidenceMap(forecastDate, leadDay)
      .then(data => { if (!cancelled) setMapData(data) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [forecastDate, leadDay])

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
      <Header modelLoaded={regions.find(r => r.slug === region)?.has_real_model} />

      <ForecastControls
        forecastDate={forecastDate}
        onForecastDateChange={setForecastDate}
        leadDay={leadDay}
        onLeadDayChange={setLeadDay}
        region={region}
        onRegionChange={handleRegionChange}
        regions={regions}
      />

      <div className="tab-bar">
        <button
          className={`tab-btn ${activeTab === 'forecast' ? 'active' : ''}`}
          onClick={() => setActiveTab('forecast')}
        >
          <span className="tab-icon">🗺</span> Forecast Map
        </button>
        <button
          className={`tab-btn ${activeTab === 'events' ? 'active' : ''}`}
          onClick={() => setActiveTab('events')}
        >
          <span className="tab-icon">⚡</span> Historical Busts
        </button>
        <button
          className={`tab-btn ${activeTab === 'model' ? 'active' : ''}`}
          onClick={() => setActiveTab('model')}
        >
          <span className="tab-icon">🤖</span> Model Info
        </button>
      </div>

      {activeTab === 'forecast' && (
        <main className="dashboard-main">
          <section className="map-panel" aria-label="Forecast map">
            <MapView
              onStateClick={handleStateClick}
              mapData={mapData}
              selectedRegion={region}
            />
          </section>
          <aside className="intel-panel" aria-label="Region intelligence">
            <RegionPanel
              region={region}
              forecastDate={forecastDate}
              leadDay={leadDay}
              apiState={apiState}
              mapNotice={mapNotice}
            />
            <div className="outlook-section">
              <h3 className="section-title">10-Day Confidence Outlook</h3>
              <OutlookChart outlookState={outlookState} currentLeadDay={leadDay} onLeadDayClick={setLeadDay} />
            </div>
          </aside>
        </main>
      )}

      {activeTab === 'events' && (
        <main className="dashboard-main events-layout">
          <BustEventsPanel events={bustEvents} onEventClick={(e) => {
            setRegion(e.slug)
            setActiveTab('forecast')
          }} />
        </main>
      )}

      {activeTab === 'model' && (
        <main className="dashboard-main model-layout">
          <ModelInfoBadge />
        </main>
      )}

      <footer className="status-bar">
        <div className="legend">
          <span className="legend-title">Bust Risk</span>
          <ul className="legend-scale">
            <li><span className="legend-swatch risk-low" aria-hidden="true" />Low (&lt;30%)</li>
            <li><span className="legend-swatch risk-medium" aria-hidden="true" />Moderate (30–60%)</li>
            <li><span className="legend-swatch risk-high" aria-hidden="true" />High (&gt;60%)</li>
          </ul>
        </div>
        <div className="status-text">
          <span className="status-dot pulse" aria-hidden="true" />
          AtmoTrust v1.0 · SIH 2026 · PS: SIH26079
        </div>
      </footer>
    </div>
  )
}

export default App