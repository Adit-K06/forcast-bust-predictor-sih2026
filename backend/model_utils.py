from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd

logger = logging.getLogger("model_utils")

# --- Paths P4 and P3 are expected to write to (per the build guide) ---------
MODEL_PATH = Path("ml/model/output/baseline_model.pkl")
FEATURES_GLOB = "ml/features/output/features_v*.parquet"

_model = None
_model_load_attempted = False


def _try_load_model():
    """Attempt to load P4's model exactly once per process, cache the result."""
    global _model, _model_load_attempted
    if _model_load_attempted:
        return _model
    _model_load_attempted = True

    if not MODEL_PATH.exists():
        logger.info("No trained model found at %s yet — using mock predictions.", MODEL_PATH)
        return None

    try:
        _model = joblib.load(MODEL_PATH)
        logger.info("Loaded real model from %s", MODEL_PATH)
    except Exception as exc:  # noqa: BLE001 — we want to fall back on any load error
        logger.warning("Found %s but failed to load it (%s) — falling back to mock.", MODEL_PATH, exc)
        _model = None

    return _model


def _latest_feature_file() -> Optional[Path]:
    """Find the newest features_vX.parquet P3 has written, if any."""
    candidates = sorted(Path(".").glob(FEATURES_GLOB))
    return candidates[-1] if candidates else None


def real_model_available() -> bool:
    """True once both P4's model and P3's feature table exist and load cleanly."""
    return _try_load_model() is not None and _latest_feature_file() is not None


def predict_real(region: str, forecast_date: date, lead_day: int):
    """
    Look up (or compute) the feature row for this region/date/lead_day from
    P3's feature table and run it through P4's model.

    Returns None if anything about the real path isn't ready yet, so the
    caller in main.py can fall back to the mock path without crashing the API.

    NOTE for P5 on Day 3: the exact column names/lookup key here must match
    whatever P3 actually produces — confirm with them and adjust the
    `feature_row = ...` line below. This function is intentionally isolated
    so that adjustment doesn't touch main.py or the API contract at all.
    """
    model = _try_load_model()
    feature_file = _latest_feature_file()
    if model is None or feature_file is None:
        return None

    try:
        features_df = pd.read_parquet(feature_file)
        # TODO (Day 3, confirm with P3): adjust column names to match their schema.
        feature_row = features_df[
            (features_df["region"] == region)
            & (features_df["date"] == pd.Timestamp(forecast_date))
            & (features_df["lead_day"] == lead_day)
        ]
        if feature_row.empty:
            logger.info("No feature row for %s/%s/day%s — falling back to mock.", region, forecast_date, lead_day)
            return None

        # TODO (Day 3): drop non-feature columns (region/date/label) before predict_proba,
        # matching exactly what P4 trained on.
        feature_cols = [c for c in feature_row.columns if c not in ("region", "date", "bust")]
        proba = model.predict_proba(feature_row[feature_cols])[0][1]  # P(bust=1)
        return float(proba)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Real prediction failed (%s) — falling back to mock.", exc)
        return None
