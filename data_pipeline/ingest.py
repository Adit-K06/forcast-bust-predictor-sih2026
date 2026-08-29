import xarray as xr
import pandas as pd
import os
import warnings
from datetime import datetime, timedelta
import glob


warnings.filterwarnings('ignore')

def process_and_align():
    """
    Day 2: Process full pilot period (7-14 days) and align GFS forecasts with ERA5 observations.

    Output: aligned_pilot.parquet with columns:
      - latitude, longitude, region, date, lead_day
      - forecast_value (GFS precipitation), observed_value (ERA5 precipitation)
    """
    os.makedirs('data_pipeline/output', exist_ok=True)
    print("=" * 60)
    print("DAY 2: Aligning forecast (GFS) with observations (ERA5)")
    print("=" * 60)


    print("\n1. Loading ERA5 reanalysis (14-day observational ground truth)...")
    era5_path = 'data_pipeline/output/era5_pilot_20230701_20230714.grib'
    if not os.path.exists(era5_path):
        print(f"   ERROR: {era5_path} not found. Run download_pilot.py first.")
        return

    era5 = xr.open_dataset(
        era5_path,
        engine='cfgrib',
        backend_kwargs={'indexpath': ''}
    )
    print(f"   ✓ Loaded ERA5: {era5.dims}")


    print("\n2. Loading GFS forecasts (regridding to ERA5 resolution)...")
    gfs_files = sorted(glob.glob('data_pipeline/output/gfs_pilot_*.grib'))
    if not gfs_files:
        print("   ERROR: No GFS files found. Run download_pilot.py first.")
        return

    print(f"   Found {len(gfs_files)} GFS files")

    all_gfs_data = []
    for gfs_file in gfs_files:
        try:
            date_str = os.path.basename(gfs_file).replace('gfs_pilot_', '').replace('.grib', '')
            gfs = xr.open_dataset(
                gfs_file,
                engine='cfgrib',
                backend_kwargs={
                    'indexpath': '',
                    'filter_by_keys': {'typeOfLevel': 'meanSea'}
                }
            )
            # Regrid to ERA5 grid
            gfs_regridded = gfs.interp(
                latitude=era5.latitude,
                longitude=era5.longitude,
                method='linear'
            )
            gfs_regridded['forecast_date'] = date_str
            all_gfs_data.append(gfs_regridded)
            print(f"   ✓ {date_str}: regridded to {gfs_regridded.dims}")
        except Exception as e:
            print(f"   ⚠ {date_str}: {str(e)}")

    if not all_gfs_data:
        print("   ERROR: Could not load any GFS files")
        return

    print("\n3. Converting to tabular format and merging...")

    df_era5 = era5.to_dataframe().reset_index()
    df_era5 = df_era5[['latitude', 'longitude', 'tp']].copy()
    df_era5.rename(columns={'tp': 'observed_value'}, inplace=True)
    print(f"   ERA5 rows: {len(df_era5)}")

    all_aligned = []
    for i, gfs_data in enumerate(all_gfs_data):
        try:
            gfs_file = gfs_files[i]
            forecast_date = os.path.basename(gfs_file).replace('gfs_pilot_', '').replace('.grib', '')
            forecast_date_obj = datetime.strptime(forecast_date, '%Y%m%d')

            df_gfs = gfs_data.to_dataframe().reset_index()
            gfs_var = [col for col in df_gfs.columns if col not in ['latitude', 'longitude', 'forecast_date']][0]
            df_gfs = df_gfs[['latitude', 'longitude', gfs_var]].copy()
            df_gfs.rename(columns={gfs_var: 'forecast_value'}, inplace=True)

            aligned_df = pd.merge(
                df_gfs,
                df_era5,
                on=['latitude', 'longitude'],
                how='inner'
            )

            aligned_df['region'] = 'Coastal Karnataka'
            aligned_df['date'] = forecast_date
            aligned_df['lead_day'] = 1

            all_aligned.append(aligned_df)
            print(f"   ✓ {forecast_date}: {len(aligned_df)} aligned cells")
        except Exception as e:
            print(f"   ⚠ Error processing {forecast_date}: {str(e)}")

    if not all_aligned:
        print("   ERROR: Could not create any aligned datasets")
        return


    final_df = pd.concat(all_aligned, ignore_index=True)
    final_df = final_df[['latitude', 'longitude', 'region', 'date', 'lead_day', 'forecast_value', 'observed_value']]


    output_path = 'data_pipeline/output/aligned_pilot.parquet'
    final_df.to_parquet(output_path, index=False)

    print("\n" + "=" * 60)
    print(f"✓ SUCCESS: Aligned dataset saved")
    print(f"  Path: {output_path}")
    print(f"  Shape: {final_df.shape}")
    print(f"  Rows: {len(final_df)} (date × location combinations)")
    print(f"  Date range: {final_df['date'].min()} to {final_df['date'].max()}")
    print(f"  Regions: {final_df['region'].unique()}")
    print("=" * 60)
    print("\n→ Share aligned_pilot.parquet with P3 (ML) and P6 (Baseline)")

if __name__ == "__main__":
    process_and_align()
