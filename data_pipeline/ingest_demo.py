import xarray as xr
import pandas as pd
import os
import warnings
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')

DEMO_EVENTS = [
    {'region_key': 'odisha', 'region_name': 'Odisha', 'date': '20230708'},
    {'region_key': 'kerala', 'region_name': 'Kerala', 'date': '20220914'},
    {'region_key': 'uttarakhand', 'region_name': 'Uttarakhand', 'date': '20230522'},
    {'region_key': 'vidarbha', 'region_name': 'Vidarbha', 'date': '20220729'},
    {'region_key': 'ap-coast', 'region_name': 'AP Coast', 'date': '20211017'},
]

def process_demo_events():
    os.makedirs('data-pipeline/output', exist_ok=True)
    logger.info("=" * 70)
    logger.info("PROCESSING 5 HISTORICAL BUST EVENTS FOR OFFLINE DEMO")
    logger.info("=" * 70)

    all_demo_data = []

    for event in DEMO_EVENTS:
        region_key = event['region_key']
        region_name = event['region_name']
        date_str = event['date']
        
        logger.info(f"\nProcessing: {region_name} on {date_str}")
        
        era5_path = f'data-pipeline/output/era5_demo_{region_key}_{date_str}.grib'
        gfs_path = f'data-pipeline/output/gfs_demo_{region_key}_{date_str}.grib'

        if not os.path.exists(era5_path) or not os.path.exists(gfs_path):
            logger.warning(f"  [SKIP] Missing GRIB files for {region_name}. Run download_demo.py first.")
            continue

        try:
            # 1. Load and format ERA5
            era5 = xr.open_dataset(era5_path, engine='cfgrib', backend_kwargs={'indexpath': ''})
            df_era5 = era5.to_dataframe().reset_index()
            
            # Find precip variable and convert to mm
            if 'tp' in df_era5.columns:
                df_era5 = df_era5[['latitude', 'longitude', 'tp']].copy()
                df_era5.rename(columns={'tp': 'observed_value'}, inplace=True)
            else:
                var_col = [c for c in df_era5.columns if c not in ['latitude', 'longitude']][0]
                df_era5 = df_era5[['latitude', 'longitude', var_col]].copy()
                df_era5.rename(columns={var_col: 'observed_value'}, inplace=True)
                
            df_era5['observed_value'] = df_era5['observed_value'] * 1000.0

            # 2. Load GFS (Surface Accumulated)
            gfs = xr.open_dataset(
                gfs_path, 
                engine='cfgrib', 
                backend_kwargs={
                    'indexpath': '',
                    'filter_by_keys': {'typeOfLevel': 'surface', 'stepType': 'accum'}
                }
            )

            # 3. Regrid GFS to ERA5
            gfs_regridded = gfs.interp(
                latitude=era5.latitude,
                longitude=era5.longitude,
                method='linear'
            )

            # Extract variable safely
            gfs_var = list(gfs_regridded.data_vars)[0]
            df_gfs = gfs_regridded.to_dataframe().reset_index()
            df_gfs = df_gfs[['latitude', 'longitude', gfs_var]].copy()
            df_gfs.rename(columns={gfs_var: 'forecast_value'}, inplace=True)

            # 4. Merge
            aligned_df = pd.merge(df_gfs, df_era5, on=['latitude', 'longitude'], how='inner')
            aligned_df['region'] = region_name
            aligned_df['date'] = date_str
            aligned_df['lead_day'] = 1

            all_demo_data.append(aligned_df)
            logger.info(f"  [OK] Successfully aligned {len(aligned_df)} cells")

        except Exception as e:
            logger.error(f"  [ERROR] Failed processing {region_name}: {str(e)}")

    # 5. Export to the offline demo Parquet
    if all_demo_data:
        final_df = pd.concat(all_demo_data, ignore_index=True)
        output_path = 'data-pipeline/output/demo_data_offline.parquet'
        final_df.to_parquet(output_path, index=False)
        
        logger.info(f"\n[OK] SUCCESS! Exported {len(final_df)} rows to {output_path}")
        logger.info("  --> Hand this file to P1 (Frontend) and P5 (Backend/Python) for the live demo.")
    else:
        logger.error("[ERROR] No demo data was generated.")

if __name__ == "__main__":
    process_demo_events()