const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function apiFetch(path) {
  const res = await fetch(`${API_BASE_URL}${path}`)
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`)
  return res.json()
}

export async function getForecastConfidence(region, date, leadDay) {
  const params = new URLSearchParams({ region, date, lead_day: String(leadDay) })
  return apiFetch(`/forecast-confidence?${params}`)
}

export async function get10DayOutlook(region, date) {
  const params = new URLSearchParams({ region, date })
  return apiFetch(`/10day-outlook?${params}`)
}

export async function getConfidenceMap(date, leadDay) {
  return apiFetch(`/confidence-map/${date}?lead_day=${leadDay}`)
}

export async function getBustEvents() {
  return apiFetch('/bust-events')
}

export async function getRegions() {
  return apiFetch('/regions')
}

export async function getModelInfo() {
  return apiFetch('/model-info')
}

export async function getSkillScore() {
  return apiFetch('/skill-score')
}