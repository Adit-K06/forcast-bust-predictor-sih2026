function BustEventsPanel({ events, onEventClick }) {
  if (!events || events.length === 0) {
    return (
      <div className="bust-events-panel">
        <div className="panel-status">Loading historical bust events…</div>
      </div>
    )
  }

  return (
    <div className="bust-events-panel">
      <h2>⚡ Historical Forecast Busts</h2>
      <p className="panel-desc">
        Curated examples of real NWP forecast failures over India, used to demonstrate AtmoTrust's
        ability to flag high-risk situations in advance. These events were all cases where GFS
        significantly underestimated observed rainfall.
      </p>

      <div className="bust-events-grid">
        {events.map((evt, i) => (
          <div
            key={i}
            className="bust-event-card"
            onClick={() => onEventClick(evt)}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && onEventClick(evt)}
            aria-label={`${evt.region} bust event on ${evt.date}`}
          >
            <div className="bust-event-date">{evt.date} · Lead Day {evt.lead_day}</div>
            <div className="bust-event-region">{evt.region}</div>
            <div className="bust-event-desc">{evt.event}</div>

            {(evt.observed_mm || evt.forecast_mm || evt.error_mm) && (
              <div className="bust-event-stats">
                {evt.observed_mm != null && (
                  <div className="bust-stat">
                    <div className="bust-stat-label">Observed</div>
                    <div className="bust-stat-value observed">{evt.observed_mm} mm</div>
                  </div>
                )}
                {evt.forecast_mm != null && (
                  <div className="bust-stat">
                    <div className="bust-stat-label">Forecast</div>
                    <div className="bust-stat-value forecast">{evt.forecast_mm} mm</div>
                  </div>
                )}
                {evt.error_mm != null && (
                  <div className="bust-stat">
                    <div className="bust-stat-label">Error</div>
                    <div className="bust-stat-value">{evt.error_mm} mm</div>
                  </div>
                )}
              </div>
            )}

            <div className="bust-cta">→ View forecast confidence for this region</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default BustEventsPanel
