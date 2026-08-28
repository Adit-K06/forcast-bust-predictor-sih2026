function Header() {
  return (
    <header className="app-header">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">FB</span>
        <div className="brand-text">
          <h1>FORECAST BUST</h1>
          <p>Forecast Reliability Intelligence</p>
        </div>
      </div>

      <div className="env-badge">
        <span className="env-dot" aria-hidden="true" />
        PROTOTYPE ENVIRONMENT
      </div>
    </header>
  )
}

export default Header