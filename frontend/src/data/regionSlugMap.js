// State name (from GeoJSON) -> backend slug
export const STATE_TO_BACKEND_SLUG = {
  'Karnataka': 'coastal-karnataka',
  'Goa': 'konkan-goa',
  'Maharashtra': 'maharashtra',
  'Tamil Nadu': 'tamil-nadu',
  'Rajasthan': 'west-rajasthan',
  'West Bengal': 'gangetic-west-bengal',
  'Bihar': 'gangetic-west-bengal',
  'Jharkhand': 'gangetic-west-bengal',
  'Uttar Pradesh': 'gangetic-west-bengal',
  'Odisha': 'gangetic-west-bengal',
  'Gujarat': 'konkan-goa',
  'Kerala': 'coastal-karnataka',
  'Andhra Pradesh': 'tamil-nadu',
}

export const BACKEND_REGIONS = [
  { slug: 'all-india', label: 'All India' },
  { slug: 'coastal-karnataka', label: 'Coastal Karnataka' },
  { slug: 'konkan-goa', label: 'Konkan & Goa' },
  { slug: 'vidarbha', label: 'Vidarbha' },
  { slug: 'maharashtra', label: 'Maharashtra' },
  { slug: 'tamil-nadu', label: 'Tamil Nadu' },
  { slug: 'west-rajasthan', label: 'West Rajasthan' },
  { slug: 'gangetic-west-bengal', label: 'Gangetic West Bengal' },
]

export function getBackendSlugForState(stateName) {
  return STATE_TO_BACKEND_SLUG[stateName] ?? null
}

export function getRegionLabel(slug) {
  const match = BACKEND_REGIONS.find(r => r.slug === slug)
  return match ? match.label : slug
}