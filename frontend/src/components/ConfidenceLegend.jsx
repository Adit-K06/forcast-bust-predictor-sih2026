const RISK_LEVELS = [
  { label: 'Low', className: 'risk-low' },
  { label: 'Medium', className: 'risk-medium' },
  { label: 'High', className: 'risk-high' },
]

function ConfidenceLegend() {
  return (
    <div className="legend">
      <span className="legend-title">Bust Risk</span>
      <ul className="legend-scale">
        {RISK_LEVELS.map(({ label, className }) => (
          <li key={label}>
            <span className={`legend-swatch ${className}`} aria-hidden="true" />
            {label}
          </li>
        ))}
      </ul>
      <span className="legend-caveat">Framework only — not live data</span>
    </div>
  )
}

export default ConfidenceLegend