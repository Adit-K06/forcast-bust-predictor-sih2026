function Header({ modelLoaded }) {
  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-logo" aria-hidden="true">
          {/* Atmosphere icon: SVG cloud with lightning */}
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M21 11.5C21 11.5 20.5 7 16 7C12.5 7 10.5 9.5 10.5 9.5C10.5 9.5 9 9 8 10C6 10.5 5 12.5 5 14C5 16.5 7 18 9.5 18H20.5C22.5 18 24 16.5 24 14.5C24 12.5 22.5 11.5 21 11.5Z" fill="rgba(56,139,253,0.25)" stroke="#388bfd" strokeWidth="1.2"/>
            <path d="M13 18L11 23L14.5 20H12.5L15 15H12L13 18Z" fill="#d29922"/>
          </svg>
        </div>
        <div className="brand-text">
          <h1>ATMOTRUST</h1>
          <p>GFS Forecast Bust Detection · SIH26079</p>
        </div>
      </div>

      <div className="header-right">
        <div className="header-tagline">
          Operational Forecast Reliability
        </div>
        <div className={`model-badge ${modelLoaded ? 'real' : 'mock'}`}>
          <span className="model-badge-dot" aria-hidden="true" />
          {modelLoaded ? 'REAL MODEL ACTIVE' : 'CALIBRATED MOCK'}
        </div>
        <div className="env-badge">PROTOTYPE</div>
      </div>
    </header>
  )
}

export default Header