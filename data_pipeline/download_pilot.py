import cdsapi
import requests
import os
from datetime import datetime, timedelta

os.makedirs("data_pipeline/output", exist_ok=True)

# Day 2: Download full 14-day pilot period (July 1-14, 2023)
# Coastal Karnataka: 15.5N, 74.0E to 12.5N, 75.5E
REGION = [15.5, 74.0, 12.5, 75.5]
START_DATE = datetime(2023, 7, 1)
END_DATE = datetime(2023, 7, 14)
DATE_RANGE = (END_DATE - START_DATE).days + 1

print(f"Downloading ERA5 and GFS data for {DATE_RANGE} days (July 1-14, 2023)...")

c = cdsapi.Client()

# Download ERA5 for all days at once (more efficient)
dates = [START_DATE + timedelta(days=i) for i in range(DATE_RANGE)]
date_strs = [d.strftime('%Y-%m-%d') for d in dates]

print("Downloading ERA5 reanalysis (observed ground truth)...")
c.retrieve(
    'reanalysis-era5-single-levels',
    {
        'product_type': 'reanalysis',
        'variable': 'total_precipitation',
        'year': '2023',
        'month': '07',
        'day': [str(d.day).zfill(2) for d in dates],
        'time': '12:00',
        'area': REGION,
        'format': 'grib',
    },
    'data_pipeline/output/era5_pilot_20230701_20230714.grib'
)
print("✓ ERA5 download complete")

# Download GFS forecasts for each day
print("Downloading GFS forecasts from AWS Open Data...")
for date in dates:
    date_str = date.strftime('%Y%m%d')
    try:
        # GFS forecast files: gfs.YYYYMMDD/00/atmos/gfs.t00z.pgrb2.0p25.fHHH
        # Lead time 024 = Day 2 forecast (issued day 1, valid day 2)
        gfs_url = f"https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{date_str}/00/atmos/gfs.t00z.pgrb2.0p25.f024"
        response = requests.get(gfs_url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(f'data_pipeline/output/gfs_pilot_{date_str}.grib', 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"  ✓ {date_str}")
        else:
            print(f"  ⚠ {date_str} not available (HTTP {response.status_code})")
    except Exception as e:
        print(f"  ⚠ {date_str} download failed: {str(e)}")

print("\nPilot data download complete. Files saved to data_pipeline/output/")