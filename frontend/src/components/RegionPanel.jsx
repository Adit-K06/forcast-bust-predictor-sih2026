import { getRegionLabel } from '../data/regionSlugMap'

function RegionPanel({ region, forecastDate, leadDay, apiState, mapNotice }) {
  return (
    <div className="region-panel">
      <div className="region-panel-header">
        <h2>Region Intelligence</h2>
        <p className="context-line">
          {getRegionLabel(region)} · Day {leadDay} · {forecastDate}
        </p>
      </div>

      {mapNotice && (
        <div className="map-unavailable-banner">
          Forecast data unavailable for {mapNotice}. The backend currently
          supports six IMD subdivisions only, not full states.
        </div>
      )}

      {apiState.status === 'loading' && (
        <div className="panel-status">Loading forecast reliability…</div>
      )}

      {apiState.status === 'error' && (
        <div className="panel-status panel-status-error">
          Unable to load forecast confidence.
        </div>
      )}

      {apiState.status === 'success' && apiState.data && (
        <div className="forecast-result">
          {apiState.data.is_mock && <span className="mock-badge">MOCK DATA</span>}

          <div className="result-row">
            <span className="result-label">Bust Probability</span>
            <span className="result-value">
              {Math.round(apiState.data.bust_probability * 100)}%
            </span>
          </div>

          <div className="result-row">
            <span className="result-label">Confidence Score</span>
            <span className="result-value">
              {Math.round(apiState.data.confidence_score * 100)}%
            </span>
          </div>

          <div className="result-block">
            <span className="result-label">Explanation</span>
            <p className="result-text">{apiState.data.explanation_text}</p>
          </div>

          <div className="result-block">
            <span className="result-label">Top Factors</span>
            <ul className="factor-list">
              {apiState.data.top_factors.map((factor) => (
                <li key={factor}>{factor}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

export default RegionPanel