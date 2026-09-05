import os
import cdsapi
import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
from tqdm import tqdm
import warnings
warnings.filterwarnings("ignore")
RAW_DIR = Path(os.getenv("RAW_DATA_DIR", "./data/raw/era5"))
RAW_DIR.mkdir(parents=True, exist_ok=True)

INDIA_AREA = [37.0, 66.0, 6.0, 98.0]  
GRID_RESOLUTION = 0.25                 

class ERA5Downloader:
    def __init__(self, raw_dir: Path = RAW_DIR):
        self.raw_dir = raw_dir
        self.client = cdsapi.Client() 

    def download_months(self, year: int, months: list[int]) -> list[Path]:
        paths = []
        for month in tqdm(months, desc=f"ERA5 {year}"):
            path = self.download_single_month(year, month)
            if path:
                paths.append(path)
        return paths

    def download_date_range(self, start_date: str, end_date: str) -> list[Path]:
        """Download ERA5 for all months in the given date range."""
        dates = pd.date_range(start_date, end_date, freq="MS")   # month-start
        paths = []
        for d in dates:
            path = self.download_single_month(d.year, d.month)
            if path:
                paths.append(path)
        return paths

    def download_single_month(self, year: int, month: int) -> Path | None:
        out_path = self.raw_dir / f"era5_{year}{month:02d}.nc"
        if out_path.exists():
            logger.debug(f"Already exists: {out_path}")
            return out_path

        logger.info(f"Requesting ERA5: {year}-{month:02d}")

        # Use "M" (month-end) for pandas <2.2 compatibility; "ME" requires 2.2+
        days_in_month = pd.date_range(
            f"{year}-{month:02d}-01",
            periods=1,
            freq="M"
        )[0].day
        days = [f"{d:02d}" for d in range(1, days_in_month + 1)]

        try:
            sl_path = self._download_single_level(year, month, days)
            pl_path = self._download_pressure_level(year, month, days)

            if sl_path and pl_path:
                merged = self._merge_sl_pl(sl_path, pl_path, out_path)
                if merged:
                    return out_path

        except Exception as e:
            logger.error(f"ERA5 download failed for {year}-{month:02d}: {e}")
            return None

    @staticmethod
    def _unzip_if_needed(path: Path) -> Path:
        """CDS API v2 returns ZIP archives even when format=netcdf is requested.
        If the file is a ZIP, extract the first .nc inside and return that path.
        """
        import zipfile
        if zipfile.is_zipfile(path):
            extract_dir = path.parent / (path.stem + "_extracted")
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(path, "r") as zf:
                nc_names = [n for n in zf.namelist() if n.endswith(".nc")]
                if not nc_names:
                    raise RuntimeError(f"No .nc file found inside ZIP: {path}")
                zf.extract(nc_names[0], extract_dir)
                nc_path = extract_dir / nc_names[0]
            path.unlink()
            nc_path.rename(path)
            logger.debug(f"Extracted ZIP to {path}")
        return path

    def _merge_sl_pl(self, sl_path: Path, pl_path: Path, out_path: Path) -> bool:
        """Merge single-level and pressure-level temp files into one final NetCDF.
        CDS API v2 may return ZIP-wrapped NetCDF files — these are extracted first.
        """
        try:
            sl_path = self._unzip_if_needed(sl_path)
            pl_path = self._unzip_if_needed(pl_path)

            for engine in ["netcdf4", "h5netcdf", "scipy"]:
                try:
                    ds_sl = xr.open_dataset(sl_path, engine=engine)
                    ds_pl = xr.open_dataset(pl_path, engine=engine)
                    break
                except Exception:
                    continue
            else:
                raise RuntimeError("Could not open ERA5 temp files with any available engine")

            merged = xr.merge([ds_sl, ds_pl], compat="override")

            # Unit conversion: ERA5 tp is in metres, convert to mm
            if "tp" in merged:
                merged["tp"] = merged["tp"] * 1000.0
                merged["tp"].attrs["units"] = "mm"
                merged["tp"].attrs["long_name"] = "Total precipitation"
                merged = merged.rename({"tp": "precipitation_mm"})

            merged.to_netcdf(out_path)
            ds_sl.close(); ds_pl.close()
            sl_path.unlink(missing_ok=True)
            pl_path.unlink(missing_ok=True)
            logger.success(f"Saved ERA5: {out_path}")
            return True
        except Exception as e:
            logger.error(f"Merge failed for {out_path.name}: {e}")
            return False

    def _download_single_level(
        self, year: int, month: int, days: list[str]
    ) -> Path | None:
        out_path = self.raw_dir / f"era5_{year}{month:02d}_sl_tmp.nc"
        try:
            self.client.retrieve(
                "reanalysis-era5-single-levels",
                {
                    "product_type": "reanalysis",
                    "variable": [
                        "total_precipitation",
                        "mean_sea_level_pressure",
                        "2m_temperature",
                        "total_column_water_vapour",
                    ],
                    "year": str(year),
                    "month": f"{month:02d}",
                    "day": days,
                    "time": ["00:00", "06:00", "12:00", "18:00"],
                    "area": INDIA_AREA,
                    "grid": [GRID_RESOLUTION, GRID_RESOLUTION],
                    "format": "netcdf",
                },
                str(out_path),
            )
            return out_path
        except Exception as e:
            logger.error(f"Single-level ERA5 failed: {e}")
            return None

    def _download_pressure_level(
        self, year: int, month: int, days: list[str]
    ) -> Path | None:
        out_path = self.raw_dir / f"era5_{year}{month:02d}_pl_tmp.nc"
        try:
            self.client.retrieve(
                "reanalysis-era5-pressure-levels",
                {
                    "product_type": "reanalysis",
                    "variable": [
                        "u_component_of_wind",
                        "v_component_of_wind",
                        "geopotential",
                    ],
                    "pressure_level": ["500", "850"],
                    "year": str(year),
                    "month": f"{month:02d}",
                    "day": days,
                    "time": ["00:00", "12:00"],
                    "area": INDIA_AREA,
                    "grid": [GRID_RESOLUTION, GRID_RESOLUTION],
                    "format": "netcdf",
                },
                str(out_path),
            )
            return out_path
        except Exception as e:
            logger.error(f"Pressure-level ERA5 failed: {e}")
            return None

    @staticmethod
    def aggregate_to_daily(ds: xr.Dataset) -> xr.Dataset:
        daily = {}

        if "precipitation_mm" in ds:
            daily["precip_obs"] = ds["precipitation_mm"].resample(time="1D").sum()

        for var in ["msl", "t2m", "tcwv"]:
            if var in ds:
                daily[var] = ds[var].resample(time="1D").mean()

        for var in ["u850", "v850", "z500"]:
            if var in ds:
                daily[var] = ds[var].resample(time="1D").mean()

        return xr.Dataset(daily)

def extract_region_daily(
    era5_path: Path,
    region_bbox: dict,
    date: str,
) -> dict:
    ds = xr.open_dataset(era5_path)
    lat_dim = "latitude" if "latitude" in ds.dims else "lat"
    lon_dim = "longitude" if "longitude" in ds.dims else "lon"

    region_ds = ds.sel(
        {
            lat_dim: slice(region_bbox["lat_max"], region_bbox["lat_min"]),
            lon_dim: slice(region_bbox["lon_min"], region_bbox["lon_max"]),
        }
    )

    region_ds = region_ds.sel(time=date, method="nearest")
    weights = np.cos(np.deg2rad(region_ds[lat_dim]))
    result = {}
    for var in region_ds.data_vars:
        try:
            weighted = region_ds[var].weighted(
                weights.broadcast_like(region_ds[var])
            )
            result[var] = float(weighted.mean([lat_dim, lon_dim]).values)
        except Exception:
            result[var] = float(region_ds[var].mean().values)

    return result

if __name__ == "__main__":
    dl = ERA5Downloader()
    paths = dl.download_months(year=2022, months=[6])
    print(f"Downloaded: {paths}")
