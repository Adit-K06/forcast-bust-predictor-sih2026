import { getRegionLabel } from '../data/regionSlugMap'

function getRiskClass(bustProb) {
  if (bustProb < 0.30) return 'risk-low'
  if (bustProb < 0.60) return 'risk-medium'
  return 'risk-high'
}

function getAdvisoryClass(label) {
  if (label === 'VERY LOW') return 'caution'
  if (label === 'LOW') return 'warning'
  return ''
}

function RegionPanel({ region, forecastDate, leadDay, apiState, mapNotice }) {
  const data = apiState.data

  return (
    <div className="region-panel">
      <div className="region-panel-header">
        <h2>Region Intelligence</h2>
        <p className="context-line">{getRegionLabel(region)}</p>
        <p className="context-meta">
          {forecastDate} &middot; Day {leadDay} lead
          {data?.is_mock === false && (
            <span style={{ color: 'var(--risk-low)', marginLeft: 8 }}>● Real model</span>
          )}
        </p>
      </div>

      {mapNotice && (
        <div className="map-unavailable-banner">
          ⚠ Forecast data unavailable for {mapNotice}. Select from the region dropdown instead.
        </div>
      )}

      {apiState.status === 'loading' && (
        <div className="panel-status">
          <div>Fetching forecast confidence…</div>
          <div className="loading-pulse">
            <span className="loading-dot" /><span className="loading-dot" /><span className="loading-dot" />
          </div>
        </div>
      )}

      {apiState.status === 'error' && (
        <div className="panel-status panel-status-error">
          ⚠ Backend unreachable. Start the FastAPI server at port 8000.
        </div>
      )}

      {apiState.status === 'success' && data && (
        <div className="forecast-result fade-in">
          {data.is_mock && <span className="mock-badge">CALIBRATED MOCK</span>}

          {/* Main confidence gauge */}
          <div className="confidence-gauge">
            <div className="gauge-header">
              <span className="gauge-label">Bust Probability</span>
              <span className={`confidence-label-badge ${data.confidence_label}`}>
                {data.confidence_label}
              </span>
            </div>
            <div className={`gauge-value ${getRiskClass(data.bust_probability)}`}>
              {Math.round(data.bust_probability * 100)}%
            </div>
            <div className="gauge-bar-track">
              <div
                className={`gauge-bar-fill ${getRiskClass(data.bust_probability)}`}
                style={{ width: `${data.bust_probability * 100}%` }}
              />
            </div>
          </div>

          {/* Metrics grid */}
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-card-label">Confidence</div>
              <div className="metric-card-value">
                {Math.round(data.confidence_score * 100)}%
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-card-label">Bust Risk</div>
              <div className="metric-card-value" style={{ color: `var(--${getRiskClass(data.bust_probability)})` }}>
                {Math.round(data.bust_probability * 100)}%
              </div>
            </div>
          </div>

          {/* Explanation */}
          <div className="explanation-card">
            <span className="explanation-title">AI Explanation</span>
            <p className="explanation-text">{data.explanation_text}</p>
          </div>

          {/* Top factors */}
          {data.top_factors?.length > 0 && (
            <div className="explanation-card">
              <span className="explanation-title">Key Risk Factors</span>
              <ul className="factor-list" role="list">
                {data.top_factors.map((f, i) => (
                  <li key={i} className="factor-item">
                    <span className="factor-dot" aria-hidden="true" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Advisory */}
          {data.advisory && (
            <div className={`advisory-card ${getAdvisoryClass(data.confidence_label)}`}>
              <strong>Advisory:</strong> {data.advisory}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default RegionPanel