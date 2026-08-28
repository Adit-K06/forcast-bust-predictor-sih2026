import cdsapi
import requests
import os

os.makedirs("data-pipeline/output", exist_ok=True)

print("Downloading ERA5 pilot data...")
c = cdsapi.Client()
c.retrieve(
    'reanalysis-era5-single-levels',
    {
        'product_type': 'reanalysis',
        'variable': 'total_precipitation',
        'year': '2023',
        'month': '07',
        'day': '01',
        'time': '12:00',
        'area': [15.5, 74.0, 12.5, 75.5], 
        'format': 'grib',
    },
    'data-pipeline/output/era5_pilot_20230701.grib'
)

print("Downloading GFS pilot data from AWS Open Data...")
gfs_url = "https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.20230701/00/atmos/gfs.t00z.pgrb2.0p25.f024"
response = requests.get(gfs_url, stream=True)
if response.status_code == 200:
    with open('data-pipeline/output/gfs_pilot_20230701.grib', 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            f.write(chunk)
    print("GFS download complete.")
else:
    print(f"GFS download failed with status code: {response.status_code}")