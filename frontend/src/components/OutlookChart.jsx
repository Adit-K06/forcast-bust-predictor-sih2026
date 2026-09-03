function getRiskClass(bustProb) {
  if (bustProb < 0.30) return 'risk-low'
  if (bustProb < 0.60) return 'risk-medium'
  return 'risk-high'
}

function OutlookChart({ outlookState, currentLeadDay, onLeadDayClick }) {
  if (outlookState.status === 'loading') {
    return (
      <div className="panel-status">
        <div className="loading-pulse">
          <span className="loading-dot" /><span className="loading-dot" /><span className="loading-dot" />
        </div>
      </div>
    )
  }

  if (outlookState.status === 'error' || !outlookState.data?.outlook) {
    return <div className="panel-status" style={{ fontSize: 12 }}>Outlook unavailable</div>
  }

  const { outlook } = outlookState.data
  const maxPct = Math.max(...outlook.map(d => d.bust_probability * 100), 1)

  return (
    <div className="outlook-chart" role="list" aria-label="10-day bust probability outlook">
      <div className="outlook-chart-header">
        <span className="outlook-axis-label">GFS bust probability by lead day — click to select</span>
      </div>
      {outlook.map(day => {
        const pct = Math.round(day.bust_probability * 100)
        const riskClass = getRiskClass(day.bust_probability)
        const isActive = day.lead_day === currentLeadDay
        const barWidth = Math.round((pct / maxPct) * 100)

        return (
          <div
            key={day.lead_day}
            className={`outlook-day-row ${isActive ? 'active' : ''}`}
            onClick={() => onLeadDayClick(day.lead_day)}
            role="listitem"
            aria-label={`Day ${day.lead_day}: ${pct}% bust probability`}
            title={`Day ${day.lead_day} — ${day.confidence_label} confidence${day.is_mock ? ' (mock)' : ''}`}
          >
            <span className="outlook-day-label">D{day.lead_day}</span>
            <div className="outlook-bar-track">
              <div
                className={`outlook-bar-fill ${riskClass}`}
                style={{ width: `${barWidth}%` }}
              />
            </div>
            <span className={`outlook-pct ${riskClass}`}>{pct}%</span>
            {isActive && <span className="outlook-active-chip">selected</span>}
          </div>
        )
      })}
      <p className="outlook-note">
        10-day forecast horizon
      </p>
    </div>
  )
}

export default OutlookChart
