# Data Pipeline

## Data Sources Confirmed (Day 1)
- **ERA5 Reanalysis**: Downloaded via Copernicus `cdsapi` using personal API token.
- **NOAA GFS Forecast**: Downloaded directly via HTTP requests from the AWS Open Data mirror (`noaa-gfs-bdp-pds`).

## Pilot Region
- **Region**: Coastal Karnataka (Approx Bounding Box: 15.5N, 74.0E to 12.5N, 75.5E)
- **Pilot Date**: July 1, 2023

## Setup
1. Place `.cdsapirc` in your user root directory.
2. Run `python download_pilot.py` to fetch the initial GRIB files.