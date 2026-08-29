const API_BASE_URL = 'http://127.0.0.1:8000'

export async function getForecastConfidence(region, date, leadDay) {
  const params = new URLSearchParams({
    region,
    date,
    lead_day: String(leadDay),
  })

  const response = await fetch(`${API_BASE_URL}/forecast-confidence?${params.toString()}`)

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  return response.json()
}