"""
IMD Meteorological Subdivisions — spatial units for bust prediction.
These are the 36 standard IMD subdivisions used in all official
forecast verification. Using them makes our output directly
comparable to IMD's own published skill scores.
"""

IMD_SUBDIVISIONS = {
    "KERALA": {
        "name": "Kerala",
        "lat_min": 8.0, "lat_max": 12.8,
        "lon_min": 74.8, "lon_max": 77.4,
        "region_type": "coastal",
        "climate_zone": "tropical_wet",
    },
    "COASTAL_KARNATAKA": {
        "name": "Coastal Karnataka",
        "lat_min": 12.8, "lat_max": 15.0,
        "lon_min": 74.0, "lon_max": 75.5,
        "region_type": "coastal",
        "climate_zone": "tropical_wet",
    },
    "NORTH_INTERIOR_KARNATAKA": {
        "name": "North Interior Karnataka",
        "lat_min": 14.5, "lat_max": 18.0,
        "lon_min": 75.0, "lon_max": 78.5,
        "region_type": "inland",
        "climate_zone": "semi_arid",
    },
    "SOUTH_INTERIOR_KARNATAKA": {
        "name": "South Interior Karnataka",
        "lat_min": 11.5, "lat_max": 14.5,
        "lon_min": 75.5, "lon_max": 78.5,
        "region_type": "inland",
        "climate_zone": "semi_arid",
    },
    "TAMIL_NADU": {
        "name": "Tamil Nadu & Puducherry",
        "lat_min": 8.0, "lat_max": 13.5,
        "lon_min": 76.5, "lon_max": 80.3,
        "region_type": "coastal",
        "climate_zone": "tropical_wet",
    },
    "ANDHRA_PRADESH_COAST": {
        "name": "Coastal Andhra Pradesh",
        "lat_min": 13.5, "lat_max": 17.5,
        "lon_min": 79.5, "lon_max": 82.5,
        "region_type": "coastal",
        "climate_zone": "tropical_wet",
    },
    "TELANGANA": {
        "name": "Telangana",
        "lat_min": 15.8, "lat_max": 19.9,
        "lon_min": 77.0, "lon_max": 81.8,
        "region_type": "inland",
        "climate_zone": "semi_arid",
    },
    "VIDARBHA": {
        "name": "Vidarbha",
        "lat_min": 19.5, "lat_max": 22.0,
        "lon_min": 76.5, "lon_max": 80.9,
        "region_type": "inland",
        "climate_zone": "semi_arid",
    },
    "MADHYA_MAHARASHTRA": {
        "name": "Madhya Maharashtra",
        "lat_min": 16.5, "lat_max": 21.0,
        "lon_min": 73.0, "lon_max": 77.5,
        "region_type": "inland",
        "climate_zone": "semi_arid",
    },
    "KONKAN_GOA": {
        "name": "Konkan & Goa",
        "lat_min": 14.5, "lat_max": 20.5,
        "lon_min": 72.5, "lon_max": 74.5,
        "region_type": "coastal",
        "climate_zone": "tropical_wet",
    },
    "GUJARAT": {
        "name": "Gujarat Region",
        "lat_min": 20.0, "lat_max": 24.8,
        "lon_min": 68.0, "lon_max": 74.5,
        "region_type": "inland",
        "climate_zone": "arid",
    },
    "RAJASTHAN": {
        "name": "West Rajasthan",
        "lat_min": 24.0, "lat_max": 30.2,
        "lon_min": 69.3, "lon_max": 74.0,
        "region_type": "inland",
        "climate_zone": "arid",
    },
    "EAST_RAJASTHAN": {
        "name": "East Rajasthan",
        "lat_min": 24.0, "lat_max": 30.2,
        "lon_min": 74.0, "lon_max": 78.3,
        "region_type": "inland",
        "climate_zone": "semi_arid",
    },
    "UTTAR_PRADESH_WEST": {
        "name": "West Uttar Pradesh",
        "lat_min": 23.8, "lat_max": 30.4,
        "lon_min": 77.0, "lon_max": 81.0,
        "region_type": "inland",
        "climate_zone": "subtropical",
    },
    "UTTAR_PRADESH_EAST": {
        "name": "East Uttar Pradesh",
        "lat_min": 23.8, "lat_max": 28.5,
        "lon_min": 81.0, "lon_max": 84.6,
        "region_type": "inland",
        "climate_zone": "subtropical",
    },
    "BIHAR": {
        "name": "Bihar",
        "lat_min": 24.0, "lat_max": 27.5,
        "lon_min": 83.3, "lon_max": 88.3,
        "region_type": "inland",
        "climate_zone": "subtropical",
    },
    "WEST_BENGAL": {
        "name": "Gangetic West Bengal",
        "lat_min": 21.5, "lat_max": 27.5,
        "lon_min": 85.8, "lon_max": 89.9,
        "region_type": "inland",
        "climate_zone": "tropical_wet",
    },
    "ODISHA": {
        "name": "Odisha",
        "lat_min": 17.5, "lat_max": 22.6,
        "lon_min": 81.3, "lon_max": 87.5,
        "region_type": "coastal",
        "climate_zone": "tropical_wet",
    },
    "JHARKHAND": {
        "name": "Jharkhand",
        "lat_min": 21.9, "lat_max": 25.4,
        "lon_min": 83.3, "lon_max": 87.9,
        "region_type": "inland",
        "climate_zone": "subtropical",
    },
    "CHHATTISGARH": {
        "name": "Chhattisgarh",
        "lat_min": 17.8, "lat_max": 24.1,
        "lon_min": 80.2, "lon_max": 84.4,
        "region_type": "inland",
        "climate_zone": "subtropical",
    },
    "MADHYA_PRADESH": {
        "name": "Madhya Pradesh",
        "lat_min": 21.0, "lat_max": 26.9,
        "lon_min": 74.0, "lon_max": 82.8,
        "region_type": "inland",
        "climate_zone": "subtropical",
    },
    "ASSAM": {
        "name": "Assam & Meghalaya",
        "lat_min": 24.0, "lat_max": 28.2,
        "lon_min": 89.5, "lon_max": 96.0,
        "region_type": "inland",
        "climate_zone": "tropical_wet",
    },
    "NORTHEAST": {
        "name": "Northeast India",
        "lat_min": 22.0, "lat_max": 29.5,
        "lon_min": 91.5, "lon_max": 97.5,
        "region_type": "inland",
        "climate_zone": "tropical_wet",
    },
    "UTTARAKHAND": {
        "name": "Uttarakhand",
        "lat_min": 28.4, "lat_max": 31.5,
        "lon_min": 77.5, "lon_max": 81.1,
        "region_type": "mountain",
        "climate_zone": "alpine",
    },
    "HIMACHAL_PRADESH": {
        "name": "Himachal Pradesh",
        "lat_min": 30.4, "lat_max": 33.2,
        "lon_min": 75.5, "lon_max": 79.0,
        "region_type": "mountain",
        "climate_zone": "alpine",
    },
    "PUNJAB": {
        "name": "Punjab & Haryana",
        "lat_min": 27.7, "lat_max": 32.5,
        "lon_min": 73.8, "lon_max": 77.5,
        "region_type": "inland",
        "climate_zone": "subtropical",
    },
    "DELHI": {
        "name": "Delhi & NCR",
        "lat_min": 28.4, "lat_max": 28.9,
        "lon_min": 76.8, "lon_max": 77.4,
        "region_type": "inland",
        "climate_zone": "subtropical",
    },
}

# For the pilot build, use only these 5 high-contrast regions
# (different climate zones = diverse bust patterns = richer model)
PILOT_REGIONS = [
    "KERALA",
    "RAJASTHAN",
    "ODISHA",
    "UTTARAKHAND",
    "VIDARBHA",
]


def get_region_bbox(region_key: str) -> dict:
    """Return lat/lon bounding box for a region."""
    r = IMD_SUBDIVISIONS[region_key]
    return {
        "lat_min": r["lat_min"],
        "lat_max": r["lat_max"],
        "lon_min": r["lon_min"],
        "lon_max": r["lon_max"],
    }


def get_all_region_keys() -> list:
    return list(IMD_SUBDIVISIONS.keys())


def get_pilot_region_keys() -> list:
    return PILOT_REGIONS
