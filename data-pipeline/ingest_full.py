import xarray as xr
import pandas as pd
import os
import warnings
import logging
import glob
from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data-pipeline/ingest.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore')


REGIONS = {
    'coastal-karnataka': 'Coastal Karnataka',
    'maharashtra': 'Maharashtra',
    'tamil-nadu': 'Tamil Nadu',
}

def process_and_align_full():
    """
    Day 3: Production-scale alignment
    - Handles multiple regions
    - Full monsoon season (June-September 2023)
    - Robust error handling
    """
    os.makedirs('data-pipeline/output', exist_ok=True)

    logger.info("=" * 70)
    logger.info("DAY 3: PRODUCTION SCALE - ALIGNING FORECAST WITH OBSERVATIONS")
    logger.info("=" * 70)
    logger.info(f"Regions: {', '.join(REGIONS.values())}")
    logger.info(f"Period: June-September 2023 (monsoon season)")
    logger.info("")

    all_aligned_data = []

    for region_key, region_name in REGIONS.items():
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing: {region_name}")
        logger.info(f"{'='*70}")

        try:
            # Check for ERA5 file
            era5_path = f'data-pipeline/output/era5_full_{region_key}.grib'
            if not os.path.exists(era5_path):
                logger.warning(f"  ⚠ ERA5 file not found: {era5_path}")
                logger.info(f"    (Run download_full.py first or check region name)")
                continue

            logger.info(f"  1. Loading ERA5 reanalysis...")
            try:
                era5 = xr.open_dataset(
                    era5_path,
                    engine='cfgrib',
                    backend_kwargs={'indexpath': ''}
                )
                logger.info(f"     [OK] Loaded: {era5.dims}")
            except Exception as e:
                logger.error(f"     [ERROR] Failed to load ERA5: {str(e)}")
                continue

            # Load GFS files for this region
            logger.info(f"  2. Loading GFS forecasts...")
            gfs_pattern = f'data-pipeline/output/gfs_full_{region_key}_*.grib'
            gfs_files = sorted(glob.glob(gfs_pattern))

            if not gfs_files:
                logger.warning(f"     [WARN] No GFS files found for {region_key}")
                logger.info(f"     Pattern: {gfs_pattern}")
                continue

            logger.info(f"     Found {len(gfs_files)} GFS files")

            # Convert ERA5 to DataFrame once
            df_era5 = era5.to_dataframe().reset_index()
            if 'tp' in df_era5.columns:
                df_era5 = df_era5[['latitude', 'longitude', 'tp']].copy()
                df_era5.rename(columns={'tp': 'observed_value'}, inplace=True)
                df_era5['observed_value'] = df_era5['observed_value'] * 1000.0  # Convert meters to mm
            else:
                # Handle other variable names
                var_col = [c for c in df_era5.columns if c not in ['latitude', 'longitude']][0]
                df_era5 = df_era5[['latitude', 'longitude', var_col]].copy()
                df_era5.rename(columns={var_col: 'observed_value'}, inplace=True)
                df_era5['observed_value'] = df_era5['observed_value'] * 1000.0  # Convert meters to mm

            # Process each GFS file
            logger.info(f"  3. Regridding and merging...")
            region_aligned = []
            success_count = 0
            fail_count = 0

            for gfs_file in gfs_files:
                forecast_date_str = os.path.basename(gfs_file).split('_')[-1].replace('.grib', '')
                try:
                    # Try to open the GRIB file - may fail if corrupted
                    try:
                        gfs = xr.open_dataset(
                            gfs_file,
                            engine='cfgrib',
                            backend_kwargs={
                                'indexpath': '',
                                'filter_by_keys': {'typeOfLevel': 'surface', 'stepType': 'accum'}
                            }
                        )
                    except Exception as grib_err:
                        # Handle corrupted GRIB files gracefully
                        if "PrematureEndOfFileError" in str(type(grib_err).__name__) or "End of resource" in str(grib_err):
                            fail_count += 1
                            logger.warning(f"     [SKIP] {forecast_date_str}: Corrupted GRIB file (incomplete download)")
                            continue
                        else:
                            raise

                    # Regrid to ERA5 grid
                    gfs_regridded = gfs.interp(
                        latitude=era5.latitude,
                        longitude=era5.longitude,
                        method='linear'
                    )

                    # Get the actual weather variable directly from xarray before flattening
                    gfs_var = list(gfs_regridded.data_vars)[0]
                    
                    df_gfs = gfs_regridded.to_dataframe().reset_index()
                    df_gfs = df_gfs[['latitude', 'longitude', gfs_var]].copy()
                    df_gfs.rename(columns={gfs_var: 'forecast_value'}, inplace=True)

                    # Merge
                    aligned_df = pd.merge(
                        df_gfs, df_era5,
                        on=['latitude', 'longitude'],
                        how='inner'
                    )

                    # Add metadata
                    aligned_df['region'] = region_name
                    aligned_df['date'] = forecast_date_str
                    aligned_df['lead_day'] = 1

                    region_aligned.append(aligned_df)
                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    logger.debug(f"     [WARN] {forecast_date_str}: {str(e)}")

            if region_aligned:
                region_df = pd.concat(region_aligned, ignore_index=True)
                region_df = region_df[['latitude', 'longitude', 'region', 'date', 'lead_day', 'forecast_value', 'observed_value']]
                all_aligned_data.append(region_df)

                logger.info(f"     [OK] Processed {success_count} days")
                if fail_count > 0:
                    logger.info(f"     [WARN] {fail_count} days skipped (corrupt/missing)")
                logger.info(f"     Result: {len(region_df)} aligned cells")
            else:
                logger.error(f"  [ERROR] No data aligned for {region_name}")

        except Exception as e:
            logger.error(f"  [ERROR] Region {region_name} processing failed: {str(e)}")
            continue

    # Combine all regions
    if all_aligned_data:
        logger.info(f"\n{'='*70}")
        logger.info("FINALIZING DATASET")
        logger.info(f"{'='*70}")

        final_df = pd.concat(all_aligned_data, ignore_index=True)
        output_path = 'data-pipeline/output/aligned_pilot.parquet'
        final_df.to_parquet(output_path, index=False)

        logger.info(f"\n[OK] SUCCESS")
        logger.info(f"  Output: {output_path}")
        logger.info(f"  Total rows: {len(final_df):,}")
        logger.info(f"  Date range: {final_df['date'].min()} to {final_df['date'].max()}")
        logger.info(f"  Regions: {', '.join(final_df['region'].unique())}")
        logger.info(f"  Columns: {', '.join(final_df.columns.tolist())}")
        logger.info(f"\n  --> Share aligned_pilot.parquet with P3 (ML) and P6 (Baseline)")
        logger.info(f"{'='*70}\n")
    else:
        logger.error("[ERROR] No data could be aligned. Check download.log and ingest.log.")

if __name__ == "__main__":
    process_and_align_full()