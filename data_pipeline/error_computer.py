import os
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
from loguru import logger
from scipy import stats
from tqdm import tqdm

from data_pipeline.imd_regions import IMD_SUBDIVISIONS, get_all_region_keys
from data_pipeline.era5_downloader import extract_region_daily

PROCESSED_DIR = Path(os.getenv("PROCESSED_DATA_DIR", "./data/processed"))
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

BUST_PERCENTILE = float(os.getenv("BUST_THRESHOLD_PERCENTILE", 90))
LEAD_DAYS = list(range(1, 11))  

MONSOON_MONTHS = {6, 7, 8, 9}

class ForecastErrorComputer:
    def __init__(
        self,
        gfs_dir: Path = Path("./data/raw/gfs"),
        era5_dir: Path = Path("./data/raw/era5"),
        out_dir: Path = PROCESSED_DIR,
    ):
        self.gfs_dir = gfs_dir
        self.era5_dir = era5_dir
        self.out_dir = out_dir

    def build_error_dataset(
        self,
        start_date: str,
        end_date: str,
        regions: list[str] | None = None,
    ) -> pd.DataFrame:
        regions = regions or get_all_region_keys()
        init_dates = pd.date_range(start_date, end_date, freq="D")

        rows = []
        for region_key in tqdm(regions, desc="Regions"):
            region_bbox = {
                k: IMD_SUBDIVISIONS[region_key][k]
                for k in ["lat_min", "lat_max", "lon_min", "lon_max"]
            }
            region_meta = IMD_SUBDIVISIONS[region_key]

            for init_date in tqdm(init_dates, desc=f"  {region_key}", leave=False):
                for lead_day in LEAD_DAYS:
                    valid_date = init_date + pd.Timedelta(days=lead_day)

                    row = self._compute_single_error(
                        region_key=region_key,
                        region_bbox=region_bbox,
                        region_meta=region_meta,
                        init_date=init_date,
                        valid_date=valid_date,
                        lead_day=lead_day,
                    )
                    if row:
                        rows.append(row)

        df = pd.DataFrame(rows)
        if df.empty:
            logger.warning("No error records computed — check data availability")
            return df

        df = self._apply_adaptive_bust_labels(df)

        out_path = self.out_dir / "forecast_errors.parquet"
        df.to_parquet(out_path, index=False)
        logger.success(f"Error dataset saved: {out_path} ({len(df):,} rows)")
        return df

    def _compute_single_error(
        self,
        region_key: str,
        region_bbox: dict,
        region_meta: dict,
        init_date: pd.Timestamp,
        valid_date: pd.Timestamp,
        lead_day: int,
    ) -> dict | None:
        try:
            precip_forecast = self._get_gfs_region_value(
                region_bbox, init_date, lead_day, variable="tp"
            )
            if precip_forecast is None:
                return None

            precip_observed = self._get_era5_region_value(
                region_bbox, valid_date, variable="precipitation_mm"
            )
            if precip_observed is None:
                return None

            abs_error = abs(precip_forecast - precip_observed)
            month = init_date.month

            return {
                "region": region_key,
                "region_type": region_meta["region_type"],
                "climate_zone": region_meta["climate_zone"],
                "init_date": init_date.date(),
                "valid_date": valid_date.date(),
                "lead_day": lead_day,
                "month": month,
                "season": self._get_season(month),
                "is_monsoon": month in MONSOON_MONTHS,
                "precip_forecast_mm": float(precip_forecast),
                "precip_observed_mm": float(precip_observed),
                "abs_error_mm": float(abs_error),
                "signed_error_mm": float(precip_forecast - precip_observed),
                "is_bust": None,
                "bust_threshold_mm": None,
            }
        except Exception as e:
            logger.debug(f"Error computing {region_key} {init_date.date()} D+{lead_day}: {e}")
            return None

    def _apply_adaptive_bust_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        thresholds = {}

        for (region, season), group in df.groupby(["region", "season"]):
            threshold = np.percentile(group["abs_error_mm"].dropna(), BUST_PERCENTILE)
            thresholds[(region, season)] = threshold

        def label_row(row):
            key = (row["region"], row["season"])
            threshold = thresholds.get(key, np.inf)
            return pd.Series({
                "is_bust": int(row["abs_error_mm"] >= threshold),
                "bust_threshold_mm": threshold,
            })

        labels = df.apply(label_row, axis=1)
        df["is_bust"] = labels["is_bust"]
        df["bust_threshold_mm"] = labels["bust_threshold_mm"]

        bust_rate = df.groupby("region")["is_bust"].mean()
        logger.info(f"Bust rates by region:\n{bust_rate.to_string()}")

        return df

    def _get_gfs_region_value(
        self,
        region_bbox: dict,
        init_date: pd.Timestamp,
        lead_day: int,
        variable: str = "tp",
    ) -> float | None:
        date_str = init_date.strftime("%Y%m%d")
        nc_path = self.gfs_dir / date_str / f"gfs_{date_str}_combined.nc"

        if not nc_path.exists():
            return None

        try:
            ds = xr.open_dataset(nc_path)
            if variable not in ds:
                alt_names = {"tp": ["APCP", "precip", "precipitation"]}
                for alt in alt_names.get(variable, []):
                    if alt in ds:
                        variable = alt
                        break

            if "lead_day" in ds.dims:
                var_data = ds[variable].sel(lead_day=lead_day, method="nearest")
            else:
                var_data = ds[variable]

            lat_dim = "latitude" if "latitude" in ds.dims else "lat"
            lon_dim = "longitude" if "longitude" in ds.dims else "lon"

            subset = var_data.sel(
                {
                    lat_dim: slice(region_bbox["lat_max"], region_bbox["lat_min"]),
                    lon_dim: slice(region_bbox["lon_min"], region_bbox["lon_max"]),
                }
            )
            weights = np.cos(np.deg2rad(subset[lat_dim]))
            weighted_mean = float(
                subset.weighted(weights.broadcast_like(subset)).mean([lat_dim, lon_dim])
            )
            return max(0.0, weighted_mean)

        except Exception as e:
            logger.debug(f"GFS read error: {e}")
            return None

    def _get_era5_region_value(
        self,
        region_bbox: dict,
        valid_date: pd.Timestamp,
        variable: str = "precipitation_mm",
    ) -> float | None:
        month_str = valid_date.strftime("%Y%m")
        era5_path = self.era5_dir / f"era5_{month_str}.nc"

        if not era5_path.exists():
            return None

        try:
            result = extract_region_daily(
                era5_path=era5_path,
                region_bbox=region_bbox,
                date=valid_date.strftime("%Y-%m-%d"),
            )
            return max(0.0, result.get(variable, result.get("tp", 0.0)))
        except Exception as e:
            logger.debug(f"ERA5 read error: {e}")
            return None

    @staticmethod
    def _get_season(month: int) -> str:
        if month in {12, 1, 2}:
            return "DJF"
        elif month in {3, 4, 5}:
            return "MAM"
        elif month in {6, 7, 8, 9}:
            return "JJAS"
        else:
            return "OND"

class RunJumpComputer:
    def __init__(self, gfs_dir: Path = Path("./data/raw/gfs")):
        self.gfs_dir = gfs_dir

    def compute_jumps(self, error_df: pd.DataFrame) -> pd.DataFrame:
        error_df = error_df.copy()
        jumps = []

        for _, row in tqdm(error_df.iterrows(), total=len(error_df), desc="Run jumps"):
            jump = self._compute_single_jump(
                region_key=row["region"],
                init_date=pd.Timestamp(row["init_date"]),
                lead_day=row["lead_day"],
            )
            jumps.append(jump)

        error_df["run_jump_mm"] = jumps
        return error_df

    def _compute_single_jump(
        self,
        region_key: str,
        init_date: pd.Timestamp,
        lead_day: int,
    ) -> float:
        region_bbox = {
            k: IMD_SUBDIVISIONS[region_key][k]
            for k in ["lat_min", "lat_max", "lon_min", "lon_max"]
        }
        ec = ForecastErrorComputer()

        f_today = ec._get_gfs_region_value(
            region_bbox, init_date, lead_day
        )
        f_yesterday = ec._get_gfs_region_value(
            region_bbox, init_date - pd.Timedelta(days=1), lead_day + 1
        )

        if f_today is None or f_yesterday is None:
            return np.nan

        return abs(f_today - f_yesterday)


if __name__ == "__main__":
    comp = ForecastErrorComputer()
    df = comp.build_error_dataset(
        start_date="2022-06-01",
        end_date="2023-09-30",
        regions=["KERALA", "RAJASTHAN", "ODISHA"],
    )
    print(df.head())
    print(f"\nBust rate: {df['is_bust'].mean():.1%}")
    print(f"Shape: {df.shape}")
