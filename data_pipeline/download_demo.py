import os
import logging
import requests
import cdsapi

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# The exact 5 historical events from the presentation deck
DEMO_EVENTS = [
    {'region_key': 'odisha', 'region_name': 'Odisha', 'date': '20230708', 'year': '2023', 'month': '07', 'day': '08', 'bbox': [23.0, 81.0, 17.5, 87.5]},
    {'region_key': 'kerala', 'region_name': 'Kerala', 'date': '20220914', 'year': '2022', 'month': '09', 'day': '14', 'bbox': [13.0, 74.5, 8.0, 77.5]},
    {'region_key': 'uttarakhand', 'region_name': 'Uttarakhand', 'date': '20230522', 'year': '2023', 'month': '05', 'day': '22', 'bbox': [31.5, 77.5, 28.5, 81.5]},
    {'region_key': 'vidarbha', 'region_name': 'Vidarbha', 'date': '20220729', 'year': '2022', 'month': '07', 'day': '29', 'bbox': [22.0, 75.5, 18.5, 81.0]},
    {'region_key': 'ap-coast', 'region_name': 'AP Coast', 'date': '20211017', 'year': '2021', 'month': '10', 'day': '17', 'bbox': [19.5, 79.5, 13.5, 84.5]},
]

def download_gfs_for_date(year, month, day, output_path):
    # Downloads Day 1 (f024) forecast from 00z run via AWS Open Data
    url = f"https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{year}{month}{day}/00/atmos/gfs.t00z.pgrb2.0p25.f024"
    logger.info(f"    Downloading GFS from AWS: {url}")
    
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"    [OK] GFS saved to {output_path}")
    else:
        logger.error(f"    [FAIL] GFS download failed with status {response.status_code}")

def download_era5_for_date(year, month, day, bbox, output_path):
    logger.info(f"    Downloading ERA5 via CDS API...")
    try:
        c = cdsapi.Client()
        c.retrieve(
            'reanalysis-era5-single-levels',
            {
                'product_type': 'reanalysis',
                'format': 'grib',
                'variable': 'total_precipitation',
                'year': year,
                'month': month,
                'day': day,
                'time': ['00:00', '06:00', '12:00', '18:00'],
                'area': bbox, # [North, West, South, East]
            },
            output_path
        )
        logger.info(f"    [OK] ERA5 saved to {output_path}")
    except Exception as e:
        logger.error(f"    [FAIL] ERA5 download failed: {str(e)}")

def download_demo_data():
    os.makedirs('data-pipeline/output', exist_ok=True)
    logger.info("=" * 70)
    logger.info("DOWNLOADING SPECIFIC HISTORICAL CASE STUDIES FOR OFFLINE DEMO")
    logger.info("=" * 70)

    for event in DEMO_EVENTS:
        region = event['region_key']
        date_str = event['date']
        
        era5_out = f"data-pipeline/output/era5_demo_{region}_{date_str}.grib"
        gfs_out = f"data-pipeline/output/gfs_demo_{region}_{date_str}.grib"
        
        logger.info(f"\nFetching {event['region_name']} for {date_str}...")
        
        if not os.path.exists(gfs_out):
            download_gfs_for_date(event['year'], event['month'], event['day'], gfs_out)
        else:
            logger.info(f"    [SKIP] GFS {date_str} already exists.")
            
        if not os.path.exists(era5_out):
            download_era5_for_date(event['year'], event['month'], event['day'], event['bbox'], era5_out)
        else:
            logger.info(f"    [SKIP] ERA5 {date_str} already exists.")

if __name__ == "__main__":
    download_demo_data()