export const STATE_TO_BACKEND_SLUG = {}

export const BACKEND_REGIONS = [
  { slug: 'all-india', label: 'All India' },
  { slug: 'coastal-karnataka', label: 'Coastal Karnataka' },
  { slug: 'konkan-goa', label: 'Konkan & Goa' },
  { slug: 'vidarbha', label: 'Vidarbha' },
  { slug: 'west-rajasthan', label: 'West Rajasthan' },
  { slug: 'gangetic-west-bengal', label: 'Gangetic West Bengal' },
]

export function getBackendSlugForState(stateName) {
  return STATE_TO_BACKEND_SLUG[stateName] ?? null
}

export function getRegionLabel(slug) {
  const match = BACKEND_REGIONS.find((r) => r.slug === slug)
  return match ? match.label : slug
}