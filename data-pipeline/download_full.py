import cdsapi
import requests
import os
import shutil
import logging
import time
from datetime import datetime, timedelta

OUTPUT_DIR = "data-pipeline/output"
LOG_FILE = "data-pipeline/download.log"

os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

REGIONS = {
    "coastal-karnataka": [15.5, 74.0, 12.5, 75.5],
    "maharashtra": [20.9, 72.8, 16.5, 75.5],
    "tamil-nadu": [13.5, 79.5, 8.0, 80.5],
}

START_DATE = datetime(2023, 6, 1)
END_DATE = datetime(2023, 9, 30)

DATE_RANGE = (END_DATE - START_DATE).days + 1

dates = [
    START_DATE + timedelta(days=i)
    for i in range(DATE_RANGE)
]

def download_era5():
    logger.info("=" * 60)
    logger.info("PHASE 1: ERA5 Reanalysis")
    logger.info("=" * 60)

    client = cdsapi.Client()

    months = {
        6: 30,
        7: 31,
        8: 31,
        9: 30,
    }

    for region_name, region_box in REGIONS.items():
        logger.info("")
        logger.info(f"Downloading ERA5 for {region_name}...")

        monthly_files = []

        for month, days_in_month in months.items():
            month_str = f"{month:02d}"

            monthly_file = os.path.join(
                OUTPUT_DIR,
                f"era5_full_{region_name}_{month_str}.grib"
            )

            if os.path.exists(monthly_file) and os.path.getsize(monthly_file) > 0:
                logger.info(
                    f"  [SKIP] ERA5 {region_name} month {month_str} already exists"
                )
                monthly_files.append(monthly_file)
                continue

            logger.info(
                f"  Downloading ERA5 {region_name}, month {month_str}..."
            )

            request_days = [
                f"{day:02d}"
                for day in range(1, days_in_month + 1)
            ]

            try:
                client.retrieve(
                    "reanalysis-era5-single-levels",
                    {
                        "product_type": "reanalysis",
                        "variable": "total_precipitation",
                        "year": "2023",
                        "month": month_str,
                        "day": request_days,
                        "time": "12:00",
                        "area": region_box,
                        "format": "grib",
                    },
                    monthly_file
                )

                if os.path.exists(monthly_file) and os.path.getsize(monthly_file) > 0:
                    monthly_files.append(monthly_file)
                    logger.info(
                        f"  [OK] ERA5 {region_name} month {month_str}"
                    )
                else:
                    logger.error(
                        f"  [ERROR] ERA5 {region_name} month {month_str}: empty file"
                    )

            except Exception as e:
                logger.error(
                    f"  [ERROR] ERA5 {region_name} month {month_str}: {e}"
                )

        if len(monthly_files) == 4:
            final_file = os.path.join(
                OUTPUT_DIR,
                f"era5_full_{region_name}.grib"
            )

            try:
                with open(final_file, "wb") as destination:
                    for monthly_file in monthly_files:
                        with open(monthly_file, "rb") as source:
                            shutil.copyfileobj(source, destination)

                logger.info(
                    f"  [OK] ERA5 {region_name}: {final_file}"
                )

            except Exception as e:
                logger.error(
                    f"  [ERROR] Could not combine ERA5 files for "
                    f"{region_name}: {e}"
                )
        else:
            logger.warning(
                f"  [WARNING] ERA5 {region_name}: "
                f"only {len(monthly_files)}/4 months available"
            )


def create_region_links(source_file, date_str):
    for region_name in REGIONS:
        region_file = os.path.join(
            OUTPUT_DIR,
            f"gfs_full_{region_name}_{date_str}.grib"
        )

        if os.path.exists(region_file):
            continue

        try:
            os.link(source_file, region_file)
            logger.info(
                f"  [LINK] {region_name} {date_str}"
            )

        except OSError:
            try:
                shutil.copy2(source_file, region_file)
                logger.info(
                    f"  [COPY] {region_name} {date_str}"
                )
            except Exception as e:
                logger.error(
                    f"  [ERROR] Could not create regional file "
                    f"{region_name} {date_str}: {e}"
                )


def download_gfs():
    logger.info("")
    logger.info("=" * 60)
    logger.info("PHASE 2: GFS Forecasts")
    logger.info("=" * 60)

    success_count = 0
    fail_count = 0
    session = requests.Session()

    for date in dates:
        date_str = date.strftime("%Y%m%d")

        source_file = os.path.join(
            OUTPUT_DIR,
            f"gfs_full_{date_str}.grib"
        )

        try:
            if os.path.exists(source_file) and os.path.getsize(source_file) > 0:
                logger.info(
                    f"  [SKIP] GFS {date_str} already downloaded"
                )
            else:
                gfs_url = (
                    f"https://noaa-gfs-bdp-pds.s3.amazonaws.com/"
                    f"gfs.{date_str}/00/atmos/"
                    f"gfs.t00z.pgrb2.0p25.f024"
                )

                logger.info(f"  Downloading GFS {date_str}...")

                response = session.get(
                    gfs_url,
                    stream=True,
                    timeout=(30, 300)
                )

                if response.status_code != 200:
                    fail_count += 1
                    logger.warning(
                        f"  [WARNING] GFS {date_str}: "
                        f"HTTP {response.status_code}"
                    )
                    time.sleep(2)
                    continue

                temp_file = source_file + ".part"

                with open(temp_file, "wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            output.write(chunk)

                response.close()

                if (
                    not os.path.exists(temp_file)
                    or os.path.getsize(temp_file) == 0
                ):
                    fail_count += 1
                    logger.warning(
                        f"  [WARNING] GFS {date_str}: empty download"
                    )

                    if os.path.exists(temp_file):
                        os.remove(temp_file)

                    continue

                os.replace(temp_file, source_file)

                success_count += 1
                logger.info(f"  [OK] GFS {date_str}")
                time.sleep(1)

            create_region_links(source_file, date_str)

        except Exception as e:
            fail_count += 1

            logger.warning(
                f"  [WARNING] GFS {date_str}: {e}"
            )

            temp_file = source_file + ".part"

            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

            time.sleep(3)
    logger.info("")
    logger.info(
        f"GFS download summary: {success_count} newly downloaded, "
        f"{fail_count} failed"
    )


def main():
    logger.info("=" * 60)
    logger.info(
        f"Starting production pipeline: "
        f"{DATE_RANGE} days x {len(REGIONS)} regions"
    )
    logger.info("=" * 60)

    download_era5()
    download_gfs()

    logger.info("")
    logger.info("=" * 60)
    logger.info("Download pipeline complete.")
    logger.info("Check data-pipeline/download.log for details.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()