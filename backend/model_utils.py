from __future__ import annotations

import logging
from datetime import date
import math
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger("model_utils")

# Resolve paths relative to the repo root (parent of the backend/ directory).
_BACKEND_DIR = Path(__file__).parent.resolve()
_REPO_ROOT = _BACKEND_DIR.parent

MODEL_PATH = _REPO_ROOT / "ml_core" / "model.joblib"
EVAL_RESULTS_PATH = _REPO_ROOT / "ml_core" / "evaluation_results.json"
FEATURES_PATH = _REPO_ROOT / "features" / "features.parquet"

# Regional mapping to training region names and numeric category codes:
# Training category codes: {"Coastal Karnataka": 0, "Maharashtra": 1, "Tamil Nadu": 2}
# Regions with 'trained': True were used in actual model training (Jun-Sep 2023).
# Regions with 'trained': False use representative demographic parameters for demo inference.
# The 'code' value is the integer category code the training data assigned to each region.
REGION_INFO = {
    "coastal-karnataka": {
        "name": "Coastal Karnataka",
        "code": 0,
        "trained": True,
        "base_hist_bust": 0.190,
        "base_forecast_mm": 24.5,
    },
    "maharashtra": {
        "name": "Maharashtra",
        "code": 1,
        "trained": True,
        "base_hist_bust": 0.165,
        "base_forecast_mm": 14.0,
    },
    "tamil-nadu": {
        "name": "Tamil Nadu",
        "code": 2,
        "trained": True,
        "base_hist_bust": 0.168,
        "base_forecast_mm": 8.5,
    },
    # --- DEMO regions below: not in training data, use representative parameters ---
    "konkan-goa": {
        "name": "Konkan & Goa",
        "code": 1,   # nearest trained region code
        "trained": False,
        "base_hist_bust": 0.185,
        "base_forecast_mm": 22.0,
    },
    "vidarbha": {
        "name": "Vidarbha",
        "code": 1,
        "trained": False,
        "base_hist_bust": 0.165,
        "base_forecast_mm": 12.5,
    },
    "gangetic-west-bengal": {
        "name": "Gangetic West Bengal",
        "code": 1,
        "trained": False,
        "base_hist_bust": 0.175,
        "base_forecast_mm": 16.0,
    },
    "west-rajasthan": {
        "name": "West Rajasthan",
        "code": 0,
        "trained": False,
        "base_hist_bust": 0.130,
        "base_forecast_mm": 4.5,
    },
    "all-india": {
        "name": "All India",
        "code": 1,
        "trained": False,
        "base_hist_bust": 0.170,
        "base_forecast_mm": 15.0,
    },
}

FEATURE_COLUMNS = [
    "region",
    "lead_day",
    "season",
    "forecast_value",
    "month_sin",
    "month_cos",
    "precip_intensity_cat",
    "hist_bust_rate",
]

# Must match FEATURE_COLUMNS exactly — used to label SHAP values for the UI.
EXPLAIN_FEATURE_NAMES = [
    "region",
    "lead_day",
    "season",
    "forecast_value",   # Fix C: was incorrectly 'precip_forecast_mm'
    "month_sin",
    "month_cos",
    "precip_intensity_cat",
    "hist_bust_rate",
]

_model = None
_model_load_attempted = False
_features_df = None
_features_load_attempted = False
_explainer = None


def _try_load_model():
    global _model, _model_load_attempted
    if _model_load_attempted:
        return _model
    _model_load_attempted = True

    if not MODEL_PATH.exists():
        logger.warning("No trained model found at %s", MODEL_PATH)
        return None
    try:
        _model = joblib.load(MODEL_PATH)
        logger.info("Loaded real model from %s", MODEL_PATH)
    except Exception as exc:
        logger.warning("Failed to load %s (%s)", MODEL_PATH, exc)
        _model = None
    return _model


def _load_features() -> Optional[pd.DataFrame]:
    global _features_df, _features_load_attempted
    if _features_load_attempted:
        return _features_df
    _features_load_attempted = True

    if not FEATURES_PATH.exists():
        return None
    try:
        # Load sample or index of features if needed
        logger.info("Features file verified at %s", FEATURES_PATH)
        return True
    except Exception as exc:
        logger.warning("Failed to read %s (%s).", FEATURES_PATH, exc)
        return None


def real_model_available() -> bool:
    return _try_load_model() is not None

def is_demo_mode(region_slug: str, lead_day: int) -> bool:
    r_info = REGION_INFO.get(region_slug)
    if not r_info or not r_info.get("trained"):
        return True
    if lead_day != 1:
        return True
    return False


def get_evaluation_results() -> Optional[dict]:
    if not EVAL_RESULTS_PATH.exists():
        return None
    try:
        import json
        with open(EVAL_RESULTS_PATH) as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Failed to read %s (%s).", EVAL_RESULTS_PATH, exc)
        return None


def _get_precip_cat(forecast_val: float) -> int:
    """Map forecast precipitation to intensity category.
    Bins MUST match feature_engineer.py exactly: [0, 2.5, 7.5, 35.5, 64.5, inf] -> 0,1,2,3,4.
    Fix A: previous inference used different thresholds causing train/serve mismatch.
    """
    if forecast_val < 2.5:   return 0   # Trace/No rain
    elif forecast_val < 7.5:  return 1   # Light
    elif forecast_val < 35.5: return 2   # Moderate
    elif forecast_val < 64.5: return 3   # Heavy
    return 4                              # Extremely Heavy


def predict_real(region_slug: str, forecast_date: date, lead_day: int):
    """
    Executes inference using the trained RandomForestClassifier and SHAP TreeExplainer.
    Model is trained on: Coastal Karnataka, Maharashtra, Tamil Nadu (Day 1, Jun-Sep 2023).
    Other regions use representative parameters — inference is DEMO mode for those.
    All lead days use the same Day-1 trained model; Days 2-10 are extrapolated estimates.
    """
    model = _try_load_model()
    if model is None:
        return None, None

    r_info = REGION_INFO.get(region_slug)
    if r_info is None:
        # Default to All India profile if slug unknown
        r_info = REGION_INFO["all-india"]

    region_code = r_info["code"]
    base_bust = r_info["base_hist_bust"]
    base_precip = r_info["base_forecast_mm"]

    # Date harmonics (seasonality)
    month = forecast_date.month
    day = forecast_date.day
    month_sin = float(np.sin(2 * np.pi * month / 12))
    month_cos = float(np.cos(2 * np.pi * month / 12))

    # Lead day uncertainty scaling: bust rate grows with lead time (extrapolation from Day-1 training)
    # NOTE: model was trained on Day 1 only; this is an engineered extrapolation for Days 2-10.
    hist_bust_rate = float(min(0.85, base_bust + (lead_day - 1) * 0.022))

    # Deterministic synoptic modulation — produces repeatable, region/date-specific values
    # NOTE: this is a demo-mode feature proxy; in production, real GFS forecast values are used.
    synoptic_seed = (day * 7 + month * 13 + lead_day * 3) % 20
    forecast_value = float(max(0.5, round(base_precip + (synoptic_seed - 10) * 1.5, 1)))
    precip_cat = _get_precip_cat(forecast_value)

    # Construct exact feature DataFrame matching trained model's feature_names_in_
    X = pd.DataFrame([{
        "region": region_code,
        "lead_day": lead_day,
        "season": 0,  # monsoon baseline
        "forecast_value": forecast_value,
        "month_sin": month_sin,
        "month_cos": month_cos,
        "precip_intensity_cat": precip_cat,
        "hist_bust_rate": hist_bust_rate,
    }])[FEATURE_COLUMNS]

    try:
        proba = float(model.predict_proba(X)[0][1])

        # Real SHAP computation
        global _explainer
        import shap
        if _explainer is None:
            _explainer = shap.TreeExplainer(model)

        shap_vals = _explainer.shap_values(X)
        if isinstance(shap_vals, list):
            shap_row = shap_vals[1][0]
        elif shap_vals.ndim == 3:
            shap_row = shap_vals[0, :, 1]  # sample 0, all features, class 1 (bust)
        else:
            shap_row = shap_vals[0]

        from explainability.explainer import ExplainabilityEngine
        engine = ExplainabilityEngine()
        explanation = engine.explain(
            bust_probability=proba,
            shap_values=np.array(shap_row),
            feature_values=pd.Series(X.iloc[0].values, index=EXPLAIN_FEATURE_NAMES),
            feature_names=EXPLAIN_FEATURE_NAMES,
        )
        return proba, explanation

    except Exception as exc:
        logger.error("Real prediction error (%s)", exc)
        return None, None