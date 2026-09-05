"""
Phase 1 — ERA5 Download Script
Runs from repo root: python scripts/download_era5.py
Downloads ERA5 reanalysis reference data for June–September 2023.
Requires a Copernicus CDS account — key is read from CDSAPI_KEY env variable or .cdsapirc.
ERA5 is a reanalysis reference field (NOT perfect ground truth).
Precipitation is automatically converted from metres to millimetres during download.
Files land in: data/raw/era5/era5_YYYYMM.nc
Already-downloaded months are automatically skipped (safe to re-run).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Inject CDS credentials from .env if .cdsapirc doesn't exist
_cdsapirc = os.path.expanduser("~/.cdsapirc")
if not os.path.exists(_cdsapirc):
    _key = os.getenv("CDSAPI_KEY", "")
    _url = os.getenv("CDSAPI_URL", "https://cds.climate.copernicus.eu/api")
    if _key:
        with open(_cdsapirc, "w") as f:
            f.write(f"url: {_url}\nkey: {_key}\n")
        print(f"Created {_cdsapirc} from environment variables")
    else:
        print("WARNING: No CDS key found. Set CDSAPI_KEY in .env or create ~/.cdsapirc")

from data_pipeline.era5_downloader import ERA5Downloader
from loguru import logger

YEAR   = 2023
MONTHS = [6, 7, 8, 9]  # June–September 2023

if __name__ == "__main__":
    logger.info(f"Starting ERA5 download: {YEAR}, months {MONTHS}")
    logger.info("ERA5 is a reanalysis reference field — precipitation auto-converted from m to mm")

    dl = ERA5Downloader()
    paths = dl.download_months(year=YEAR, months=MONTHS)

    logger.success(f"ERA5 download complete: {len(paths)}/{len(MONTHS)} months saved to data/raw/era5/")
    for p in paths:
        logger.info(f"  {p}")

    if paths:
        import xarray as xr
        sample = xr.open_dataset(paths[0])
        logger.info(f"Sample variables: {list(sample.data_vars)}")
        if "precipitation_mm" in sample:
            precip = sample["precipitation_mm"]
            logger.info(f"Precipitation units: {precip.attrs.get('units', 'mm')} — range: {float(precip.min()):.3f}–{float(precip.max()):.3f}")
        sample.close()
