# Builds the feature matrix fed to the bust-prediction model.
# Input: error_df from error_computer.py
# Output: feature DataFrame ready for XGBoost/LightGBM training

import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
from loguru import logger
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm
import warnings
warnings.filterwarnings("ignore")

from data_pipeline.imd_regions import IMD_SUBDIVISIONS

FEATURE_STORE_DIR = Path("./data/features")
FEATURE_STORE_DIR.mkdir(parents=True, exist_ok=True)


class FeatureEngineer:

    def __init__(
        self,
        gfs_dir: Path = Path("./data/raw/gfs"),
        climatology_window_years: int = 2,
    ):
        self.gfs_dir = gfs_dir
        self.climatology_window_years = climatology_window_years
        self._climatology_cache = {}
        self._analogue_model = None
        self._analogue_train_df = None



    def build_features(self, error_df: pd.DataFrame) -> pd.DataFrame:
        """Run all feature steps in order and return the enriched DataFrame."""
        logger.info(f"Building features for {len(error_df):,} records...")
        df = error_df.copy()
        df["init_date"] = pd.to_datetime(df["init_date"])
        df = df.sort_values(["region", "init_date", "lead_day"])

        # Temporal features first — month column is needed by later steps
        df = self._add_temporal_features(df)
        df = self._add_region_features(df)
        # hist_bust_rate must be computed before train/test split to avoid leakage
        df = self._add_historical_bust_rate(df)
        df = self._add_rolling_error_features(df)
        df = self._add_forecast_features(df)
        df = self._add_atmospheric_features(df)
        df = self._add_anomaly_features(df)
        df = self._add_analogue_bust_rate(df)
        df = self._add_lead_day_features(df)

        feature_cols = self._get_feature_columns(df)
        missing_pct = df[feature_cols].isnull().mean() * 100
        high_missing = missing_pct[missing_pct > 20]
        if not high_missing.empty:
            logger.warning(f"High missing features (>20%):\n{high_missing}")

        logger.success(f"Features built: {len(feature_cols)} features, {len(df):,} rows")
        return df

    def get_feature_matrix(
        self, df: pd.DataFrame, fill_missing: bool = True
    ) -> tuple[pd.DataFrame, pd.Series | None]:
        """Returns (X, y). y is None during inference when is_bust column isn't present."""
        feature_cols = self._get_feature_columns(df)
        X = df[feature_cols].copy()

        y = df["is_bust"].astype(int) if "is_bust" in df.columns else None

        if fill_missing:
            for col in X.columns:
                if X[col].isnull().any():
                    X[col] = X[col].fillna(X[col].median())

        return X, y



    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        # month kept as int so _add_anomaly_features can groupby on it
        doy = df["init_date"].dt.dayofyear
        month = df["init_date"].dt.month

        # month is kept as a plain integer column for use in _add_anomaly_features groupby
        df["month"] = month
        df["month_sin"] = np.sin(2 * np.pi * month / 12)
        df["month_cos"] = np.cos(2 * np.pi * month / 12)
        df["doy_sin"] = np.sin(2 * np.pi * doy / 365)
        df["doy_cos"] = np.cos(2 * np.pi * doy / 365)
        return df

    def _add_region_features(self, df: pd.DataFrame) -> pd.DataFrame:
        climate_dummies = pd.get_dummies(df["climate_zone"], prefix="climate", drop_first=False)
        region_dummies = pd.get_dummies(df["region_type"], prefix="rtype", drop_first=False)
        season_dummies = pd.get_dummies(df["season"], prefix="season", drop_first=False)
        df = pd.concat([df, climate_dummies, region_dummies, season_dummies], axis=1)
        return df

    def _add_historical_bust_rate(self, df: pd.DataFrame) -> pd.DataFrame:
        # compute on training data only — calling this after splitting would leak labels
        if "is_bust" not in df.columns:
            df["hist_bust_rate"] = np.nan
            df["hist_bust_rate_overall"] = np.nan
            return df

        bust_rates = (
            df.groupby(["region", "season", "lead_day"])["is_bust"]
            .mean()
            .reset_index()
            .rename(columns={"is_bust": "hist_bust_rate"})
        )
        df = df.merge(bust_rates, on=["region", "season", "lead_day"], how="left")

        overall_rates = (
            df.groupby(["region", "season"])["is_bust"]
            .mean()
            .reset_index()
            .rename(columns={"is_bust": "hist_bust_rate_overall"})
        )
        df = df.merge(overall_rates, on=["region", "season"], how="left")
        return df

    def _add_rolling_error_features(self, df: pd.DataFrame) -> pd.DataFrame:
        # 7-day rolling error catches recent model drift; trend catches worsening patterns
        if "abs_error_mm" not in df.columns:
            df["rolling_error_7d"] = np.nan
            df["rolling_error_14d"] = np.nan
            df["error_trend_7d"] = np.nan
            return df

        df = df.sort_values(["region", "lead_day", "init_date"])

        def rolling_stats(group):
            errors = group["abs_error_mm"]
            group["rolling_error_7d"] = errors.rolling(7, min_periods=3).mean()
            group["rolling_error_14d"] = errors.rolling(14, min_periods=5).mean()
            group["error_trend_7d"] = (
                errors.rolling(7, min_periods=3)
                .apply(lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True)
            )
            return group

        df = df.groupby(["region", "lead_day"], group_keys=False).apply(rolling_stats)
        return df

    def _add_forecast_features(self, df: pd.DataFrame) -> pd.DataFrame:
        # log transform handles the heavy right skew in precipitation distributions
        if "precip_forecast_mm" in df.columns:
            df["log_precip_forecast"] = np.log1p(df["precip_forecast_mm"])
            bins = [0, 2.5, 7.5, 35.5, 64.5, np.inf]
            df["precip_intensity_cat"] = pd.cut(
                df["precip_forecast_mm"], bins=bins, labels=[0, 1, 2, 3, 4]
            ).astype(float)
        return df

    def _add_atmospheric_features(self, df: pd.DataFrame) -> pd.DataFrame:
        # reads the combined NetCDF written by GFSDownloader; fills NaN if file is missing
        atmos_rows = []

        groups = df.groupby(["region", "init_date"])
        for (region_key, date), group in tqdm(groups, desc="Atmospheric features", total=groups.ngroups):
            date_str = pd.Timestamp(date).strftime("%Y%m%d")
            nc_path = self.gfs_dir / date_str / f"gfs_{date_str}_combined.nc"
            lead_day = group["lead_day"].iloc[0]

            base_row = {
                "region": region_key,
                "init_date": date,
                "pressure_gradient": np.nan,
                "wind_shear_850": np.nan,
                "wind_speed_850": np.nan,
                "pwat_value": np.nan,
                "has_depression_proxy": 0,
                "has_wd_proxy": 0,
            }

            if not nc_path.exists():
                atmos_rows.append(base_row)
                continue

            try:
                ds = xr.open_dataset(nc_path)
                bbox = {k: IMD_SUBDIVISIONS[region_key][k]
                        for k in ["lat_min", "lat_max", "lon_min", "lon_max"]}

                lat_dim = "latitude" if "latitude" in ds.dims else "lat"
                lon_dim = "longitude" if "longitude" in ds.dims else "lon"

                ds_ld = ds.sel(lead_day=lead_day, method="nearest") if "lead_day" in ds.dims else ds

                # 1° buffer for gradient computation
                wide = {
                    "lat_min": bbox["lat_min"] - 1, "lat_max": bbox["lat_max"] + 1,
                    "lon_min": bbox["lon_min"] - 1, "lon_max": bbox["lon_max"] + 1,
                }
                subset = ds_ld.sel({
                    lat_dim: slice(wide["lat_max"], wide["lat_min"]),
                    lon_dim: slice(wide["lon_min"], wide["lon_max"]),
                })

                atmos_rows.append({
                    "region": region_key,
                    "init_date": date,
                    "pressure_gradient": self._compute_gradient_magnitude(subset, "prmsl", lat_dim, lon_dim),
                    "wind_speed_850": self._compute_wind_speed(subset, lat_dim, lon_dim),
                    "wind_shear_850": self._compute_wind_shear(subset, lat_dim, lon_dim),
                    "pwat_value": float(subset.get("pwat", subset.get("tcwv", xr.DataArray(np.nan))).mean()),
                    "has_depression_proxy": int(self._detect_depression_proxy(subset, lat_dim, lon_dim)),
                    "has_wd_proxy": int(self._detect_wd_proxy(ds_ld, lat_dim, lon_dim)),
                })

            except Exception as e:
                logger.debug(f"Atmospheric feature error {region_key} {date}: {e}")
                atmos_rows.append(base_row)

        atmos_df = pd.DataFrame(atmos_rows)
        atmos_df["init_date"] = pd.to_datetime(atmos_df["init_date"])
        df["init_date"] = pd.to_datetime(df["init_date"])
        df = df.merge(atmos_df, on=["region", "init_date"], how="left")
        return df

    def _add_anomaly_features(self, df: pd.DataFrame) -> pd.DataFrame:
        # z-score each variable against its (region, month) climatological distribution
        for var in ["pwat_value", "wind_speed_850", "pressure_gradient"]:
            if var not in df.columns:
                continue
            clim_mean = df.groupby(["region", "month"])[var].transform("mean")
            clim_std = df.groupby(["region", "month"])[var].transform("std")
            df[f"{var}_anomaly"] = (df[var] - clim_mean) / (clim_std + 1e-6)

        return df

    def _add_analogue_bust_rate(self, df: pd.DataFrame) -> pd.DataFrame:
        # KNN on synoptic features: "how often did similar past patterns bust?"
        analogue_features = ["wind_speed_850", "pressure_gradient", "pwat_value",
                              "month_sin", "month_cos"]
        available = [f for f in analogue_features if f in df.columns]

        if len(available) < 3 or "is_bust" not in df.columns:
            df["analogue_bust_rate"] = np.nan
            return df

        mask = df[available].notnull().all(axis=1)
        if mask.sum() < 20:
            df["analogue_bust_rate"] = np.nan
            return df

        df = df.reset_index(drop=True)
        mask = df[available].notnull().all(axis=1)

        X_sub = df.loc[mask, available].fillna(0).values
        y_sub = df.loc[mask, "is_bust"].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_sub)

        k = min(10, mask.sum() - 1)
        knn = NearestNeighbors(n_neighbors=k + 1, metric="euclidean")  # +1 to exclude self
        knn.fit(X_scaled)

        # Map from mask-filtered position back to original df index
        masked_positions = np.where(mask)[0]
        analogue_rates = np.full(len(df), np.nan)

        for pos_in_filtered, orig_idx in enumerate(masked_positions):
            scaled_row = X_scaled[pos_in_filtered].reshape(1, -1)
            _, indices = knn.kneighbors(scaled_row)
            neighbor_indices = indices[0][1:]  # skip the point itself
            analogue_rates[orig_idx] = y_sub[neighbor_indices].mean()

        df["analogue_bust_rate"] = analogue_rates
        return df

    def _add_lead_day_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["lead_day_sq"] = df["lead_day"] ** 2
        df["lead_day_log"] = np.log(df["lead_day"])
        df["lead_day_norm"] = (df["lead_day"] - 1) / 9   # normalised to [0, 1]
        return df



    @staticmethod
    def _compute_gradient_magnitude(ds: xr.Dataset, var: str, lat_dim: str, lon_dim: str) -> float:
        data = None
        for name in [var, var.upper(), var.lower()]:
            if name in ds:
                data = ds[name]
                break
        if data is None:
            return np.nan
        if "time" in data.dims:
            data = data.isel(time=0)
        vals = data.values.squeeze()
        if vals.ndim != 2:
            return np.nan
        dy, dx = np.gradient(vals)
        return float(np.nanmean(np.sqrt(dx**2 + dy**2)))

    @staticmethod
    def _compute_wind_speed(ds: xr.Dataset, lat_dim: str, lon_dim: str) -> float:
        u = v = None
        for name in ["u850", "u", "UGRD"]:
            if name in ds:
                u = ds[name]
                break
        for name in ["v850", "v", "VGRD"]:
            if name in ds:
                v = ds[name]
                break
        if u is None or v is None:
            return np.nan
        if "time" in u.dims:
            u = u.isel(time=0)
        if "time" in v.dims:
            v = v.isel(time=0)
        return float(np.nanmean(np.sqrt(u.values**2 + v.values**2)))

    @staticmethod
    def _compute_wind_shear(ds: xr.Dataset, lat_dim: str, lon_dim: str) -> float:
        # simplified: real shear needs two pressure levels; using 850 hPa speed for now
        return FeatureEngineer._compute_wind_speed(ds, lat_dim, lon_dim)

    @staticmethod
    def _detect_depression_proxy(ds: xr.Dataset, lat_dim: str, lon_dim: str) -> bool:
        # real depressions sit at 996-1004 hPa; anything below 1000 hPa triggers this flag
        for name in ["prmsl", "PRMSL", "msl"]:
            if name in ds:
                mslp = ds[name]
                if "time" in mslp.dims:
                    mslp = mslp.isel(time=0)
                min_pressure = float(mslp.min())
                if min_pressure > 2000:   # convert Pa → hPa
                    min_pressure /= 100
                return min_pressure < 1000
        return False

    @staticmethod
    def _detect_wd_proxy(ds: xr.Dataset, lat_dim: str, lon_dim: str) -> bool:
        # WDs appear as Z500 troughs at 25-35°N, 60-75°E; climatological mean ~5700-5900 gpm
        for name in ["gh500", "z500", "HGT", "z"]:
            if name in ds:
                z = ds[name]
                if "time" in z.dims:
                    z = z.isel(time=0)
                try:
                    wd_region = z.sel({
                        lat_dim: slice(35, 25),
                        lon_dim: slice(60, 75),
                    })
                    return float(wd_region.mean()) < 5700
                except Exception:
                    return False
        return False



    @staticmethod
    def _get_feature_columns(df: pd.DataFrame) -> list[str]:
        exclude = {
            "region", "init_date", "valid_date", "is_bust",
            "abs_error_mm", "signed_error_mm", "precip_observed_mm",
            "bust_threshold_mm", "region_type", "climate_zone", "season", "month",
        }
        return [
            c for c in df.columns
            if c not in exclude and np.issubdtype(df[c].dtype, np.number)
        ]


if __name__ == "__main__":
    error_df = pd.read_parquet("./data/processed/forecast_errors.parquet")
    fe = FeatureEngineer()
    feature_df = fe.build_features(error_df)
    X, y = fe.get_feature_matrix(feature_df)
    print(f"Feature matrix: {X.shape}")
    print(f"Bust rate: {y.mean():.1%}")
    print(f"\nFeature columns:\n{list(X.columns)}")
    feature_df.to_parquet("./data/features/features.parquet", index=False)
