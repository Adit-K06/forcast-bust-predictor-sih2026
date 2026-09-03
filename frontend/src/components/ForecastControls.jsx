import { BACKEND_REGIONS } from '../data/regionSlugMap'

function ForecastControls({
  forecastDate,
  onForecastDateChange,
  leadDay,
  onLeadDayChange,
  region,
  onRegionChange,
  regions = [],
}) {
  // Use API regions if available, fall back to static list
  const displayRegions = regions.length > 0
    ? regions.map(r => ({ slug: r.slug, label: r.label }))
    : BACKEND_REGIONS

  return (
    <section className="controls-bar" aria-label="Forecast controls">
      <div className="control-group">
        <label htmlFor="forecast-date">Forecast Date</label>
        <input
          id="forecast-date"
          type="date"
          value={forecastDate}
          min="2023-06-01"
          max="2023-09-30"
          onChange={e => onForecastDateChange(e.target.value)}
        />
      </div>

      <div className="control-group lead-day-group">
        <label htmlFor="lead-day">
          Lead Day <span className="lead-day-value">Day {leadDay}</span>
        </label>
        <div className="slider-track">
          <span className="slider-endpoint">D1</span>
          <input
            id="lead-day"
            type="range"
            min="1"
            max="10"
            step="1"
            value={leadDay}
            onChange={e => onLeadDayChange(Number(e.target.value))}
            aria-valuemin={1}
            aria-valuemax={10}
            aria-valuenow={leadDay}
            aria-label={`Lead day, currently Day ${leadDay}`}
          />
          <span className="slider-endpoint">D10</span>
        </div>
      </div>

      <div className="control-group">
        <label htmlFor="region-select">Region</label>
        <select
          id="region-select"
          value={region}
          onChange={e => onRegionChange(e.target.value)}
        >
          {displayRegions.map(({ slug, label }) => (
            <option key={slug} value={slug}>{label}</option>
          ))}
        </select>
      </div>
    </section>
  )
}

export default ForecastControls