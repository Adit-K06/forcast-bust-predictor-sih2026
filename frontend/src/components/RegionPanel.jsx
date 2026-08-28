const PENDING_FIELDS = [
  'Bust probability',
  'Confidence score',
  'Explanation',
  'Top contributing factors',
]

function formatRegionLabel(region) {
  return region
    .split('-')
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(' ')
}

function RegionPanel({ forecastDate, leadDay, region }) {
  return (
    <div className="region-panel">
      <div className="region-panel-header">
        <h2>Region Intelligence</h2>
        <p className="context-line">
          {formatRegionLabel(region)} · Day {leadDay} · {forecastDate}
        </p>
      </div>

      <div className="empty-state">
        <div className="empty-icon" aria-hidden="true">
          <svg viewBox="0 0 48 48" width="40" height="40" fill="none">
            <circle cx="24" cy="20" r="7" stroke="currentColor" strokeWidth="2" />
            <path
              d="M24 27v14M14 41h20"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </div>
        <p className="empty-title">Select a region on the map</p>
        <p className="empty-subtitle">to inspect forecast reliability.</p>
      </div>

      <dl className="pending-fields">
        {PENDING_FIELDS.map((field) => (
          <div className="pending-row" key={field}>
            <dt>{field}</dt>
            <dd>—</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

export default RegionPanel