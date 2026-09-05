"""
Phase 1 — GFS Download Script
Runs from repo root: python scripts/download_gfs.py
Downloads GFS 0.25-degree forecasts for June–September 2023 (the training period).
Source: NOAA NOMADS (public, no key required). Falls back to AWS S3 if NOMADS fails.
Files land in: data/raw/gfs/YYYYMMDD/gfs_YYYYMMDD_combined.nc
Already-downloaded dates are automatically skipped (safe to re-run).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.gfs_downloader import GFSDownloader
from loguru import logger

START_DATE = "2023-06-01"
END_DATE   = "2023-09-30"
RUN_HOUR   = 0   # 00Z initialisation

if __name__ == "__main__":
    logger.info(f"Starting GFS download: {START_DATE} to {END_DATE}, run hour {RUN_HOUR:02d}Z")
    logger.info("Source: NOAA NOMADS (public). Falls back to AWS S3 if NOMADS unavailable.")

    dl = GFSDownloader()
    paths = dl.download_date_range(
        start_date=START_DATE,
        end_date=END_DATE,
        run_hour=RUN_HOUR,
        use_aws_fallback=True,
    )

    logger.success(f"GFS download complete: {len(paths)} date files saved to data/raw/gfs/")
    if paths:
        import xarray as xr
        sample = xr.open_dataset(paths[0])
        logger.info(f"Sample file variables: {list(sample.data_vars)}")
        logger.info(f"Sample file dims: {dict(sample.dims)}")
        sample.close()
