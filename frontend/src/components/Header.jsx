function Header({ modelLoaded }) {
  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-logo" aria-hidden="true">🌩</div>
        <div className="brand-text">
          <h1>ATMOTRUST</h1>
          <p>AI Forecast Bust Detection · SIH26079</p>
        </div>
      </div>

      <div className="header-right">
        <div className={`model-badge ${modelLoaded ? 'real' : 'mock'}`}>
          <span className="model-badge-dot" aria-hidden="true" />
          {modelLoaded ? 'REAL MODEL' : 'CALIBRATED MOCK'}
        </div>
        <div className="env-badge">PROTOTYPE</div>
      </div>
    </header>
  )
}

export default Header