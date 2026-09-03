import { getRegionLabel } from '../data/regionSlugMap'

function getRiskClass(bustProb) {
  if (bustProb < 0.30) return 'risk-low'
  if (bustProb < 0.60) return 'risk-medium'
  return 'risk-high'
}

function getRiskLabel(bustProb) {
  if (bustProb < 0.30) return 'Low Risk'
  if (bustProb < 0.60) return 'Moderate Risk'
  return 'High Risk'
}

function parseFactors(factors) {
  if (!factors || factors.length === 0) return []
  const weights = [1.0, 0.65, 0.40]
  return factors.slice(0, 3).map((phrase, i) => ({
    phrase,
    weight: weights[i] ?? 0.30,
  }))
}

function BustSpectrumBar({ bustProb }) {
  const pct = Math.round(bustProb * 100)
  return (
    <div className="spectrum-container">
      <div className="spectrum-bar">
        <div className="spectrum-track" />
        {/* Triangle marker */}
        <div
          className="spectrum-marker"
          style={{ left: `calc(${pct}% - 6px)` }}
          title={`Bust probability: ${pct}%`}
        />
      </div>
      <div className="spectrum-ticks">
        <span>0%</span>
        <span style={{ position: 'absolute', left: '30%' }}>30%</span>
        <span style={{ position: 'absolute', left: '60%' }}>60%</span>
        <span style={{ marginLeft: 'auto' }}>100%</span>
      </div>
      <div className="spectrum-legend-inline">
        <span className="sleg risk-low">Low</span>
        <span className="sleg risk-medium">Moderate</span>
        <span className="sleg risk-high">High</span>
      </div>
    </div>
  )
}

function SHAPFactorBars({ factors }) {
  const parsed = parseFactors(factors)
  if (parsed.length === 0) return null

  return (
    <div className="shap-factors">
      <div className="shap-header">
        <span className="section-label">Contributing Factors</span>
      </div>
      <p className="shap-subtitle">
        Ranked drivers of GFS bust risk
      </p>
      {parsed.map((f, i) => (
        <div key={i} className="shap-row">
          <span className="shap-rank">#{i + 1}</span>
          <div className="shap-bar-wrap">
            <div
              className="shap-bar-fill"
              style={{ width: `${Math.round(f.weight * 100)}%` }}
            />
          </div>
          <span className="shap-phrase">{f.phrase}</span>
        </div>
      ))}
    </div>
  )
}

function RegionPanel({ region, forecastDate, leadDay, apiState, mapNotice }) {
  const data = apiState.data

  return (
    <div className="region-panel">
      <div className="region-panel-header">
        <div className="region-panel-title-row">
          <h2>Region Intelligence</h2>
          <span className="panel-tag">GFS Bust Detection</span>
        </div>
        <p className="context-line">{getRegionLabel(region)}</p>
        <p className="context-meta">
          {forecastDate} &middot; Day {leadDay} lead
          {data?.is_mock === false && (
            <span className="real-model-tag">● Real Model</span>
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

          {/* ── Hero: Bust Probability ── */}
          <div className="bust-hero">
            <div className="bust-hero-left">
              <span className="bust-hero-label">GFS Bust Probability</span>
              <div className={`bust-hero-pct ${getRiskClass(data.bust_probability)}`}>
                {Math.round(data.bust_probability * 100)}%
              </div>
              <div className="bust-hero-risk-label">
                <span className={`risk-pill ${getRiskClass(data.bust_probability)}`}>
                  {getRiskLabel(data.bust_probability)}
                </span>
                <span className="conf-label-text">
                  {data.confidence_label} Confidence
                </span>
              </div>
            </div>
            <div className="bust-hero-right">
              <div className="mini-metric">
                <div className="mini-metric-val">
                  {Math.round(data.confidence_score * 100)}%
                </div>
                <div className="mini-metric-label">Forecast Reliability</div>
              </div>
            </div>
          </div>

          {/* ── Probability Spectrum Bar ── */}
          <BustSpectrumBar bustProb={data.bust_probability} />

          {/* ── SHAP Explanation ── */}
          <div className="explanation-card editorial">
            <div className="explanation-header-row">
              <span className="section-label">AI Analysis</span>
              <span className="shap-powered-tag">TreeExplainer</span>
            </div>
            <p className="explanation-text">{data.explanation_text}</p>
          </div>

          {/* ── SHAP Factor Bars ── */}
          {data.top_factors?.length > 0 && (
            <SHAPFactorBars factors={data.top_factors} />
          )}

          {/* ── Advisory ── */}
          {data.advisory && (
            <div className={`advisory-card ${data.bust_probability >= 0.60 ? 'risk-high' : data.bust_probability >= 0.30 ? 'risk-medium' : 'risk-low'}`}>
              <div className="advisory-icon">⚠</div>
              <div>
                <strong className="advisory-label">Operational Advisory</strong>
                <p className="advisory-text">{data.advisory}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default RegionPanel