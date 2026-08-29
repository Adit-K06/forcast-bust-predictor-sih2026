"""
FastAPI Backend — AtmoTrust Inference API

Endpoints:
  GET  /health                       — health check
  GET  /regions                      — list all IMD subdivisions
  POST /forecast-confidence          — main inference endpoint
  GET  /forecast-confidence/{region} — confidence for all lead days in a region
  GET  /confidence-map/{date}        — all regions for one date (map view)
  GET  /bust-events                  — known historical bust events
  GET  /model-info                   — model metadata and evaluation metrics

Run locally:
  uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Literal
import joblib
from loguru import logger

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_pipeline.imd_regions import IMD_SUBDIVISIONS, PILOT_REGIONS
from data_pipeline.gfs_downloader import KNOWN_BUST_EVENTS
from features.feature_engineer import FeatureEngineer
from explainability.explainer import ExplainabilityEngine, explain_single_prediction, _confidence_label, _confidence_color

# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AtmoTrust — Forecast Bust Detection API",
    description=(
        "AI-powered forecast confidence scoring for Indian medium-range weather forecasts. "
        "Predicts the probability that a GFS/NWP forecast will bust for a given region and lead day, "
        "with SHAP-based meteorological explanations. "
        "Built for SIH 2026, Problem Statement SIH26079."
    ),
    version="1.0.0",
    contact={"name": "AtmoTrust Team", "email": "team@atmotrust.dev"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Globals — loaded once at startup, shared across all requests
MODEL = None
FEATURE_DF = None
EVAL_RESULTS = None
FEATURE_ENGINEER = FeatureEngineer()
EXPLAINABILITY_ENGINE = ExplainabilityEngine()

MODEL_PATH = Path(os.getenv("MODEL_DIR", "./models")) / "ensemble_model.joblib"
FEATURE_PATH = Path("./data/features/features.parquet")
EVAL_PATH = Path(os.getenv("MODEL_DIR", "./models")) / "evaluation_results.json"


@app.on_event("startup")
async def load_model():
    global MODEL, FEATURE_DF, EVAL_RESULTS
    try:
        if MODEL_PATH.exists():
            MODEL = joblib.load(MODEL_PATH)
            logger.info(f"Model loaded from {MODEL_PATH}")
        else:
            logger.warning(f"No model found at {MODEL_PATH} — serving mock predictions")

        if FEATURE_PATH.exists():
            FEATURE_DF = pd.read_parquet(FEATURE_PATH)
            FEATURE_DF["init_date"] = pd.to_datetime(FEATURE_DF["init_date"])
            logger.info(f"Feature store loaded: {FEATURE_DF.shape}")

        if EVAL_PATH.exists():
            with open(EVAL_PATH) as f:
                EVAL_RESULTS = json.load(f)
    except Exception as e:
        logger.error(f"Startup error: {e}")


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ConfidenceRequest(BaseModel):
    region: str = Field(..., description="IMD subdivision key e.g. 'KERALA'")
    date: str = Field(..., description="Forecast init date YYYY-MM-DD")
    lead_day: int = Field(..., ge=1, le=10, description="Lead day (1=tomorrow, 10=10 days ahead)")

class TopFactor(BaseModel):
    feature: str
    shap_value: float
    feature_value: Optional[float]
    phrase: str

class ConfidenceResponse(BaseModel):
    region: str
    region_name: str
    date: str
    lead_day: int
    bust_probability: float = Field(..., description="P(forecast bust) — higher = worse")
    confidence: float = Field(..., description="1 - bust_probability")
    confidence_label: Literal["HIGH", "MODERATE", "LOW", "VERY LOW"]
    confidence_color: str
    summary: str = Field(..., description="Human-readable explanation")
    detail: str
    advisory: str
    top_factors: list[TopFactor]
    data_source: str = "GFS 0.25° + ERA5 reanalysis"

class RegionConfidenceMap(BaseModel):
    date: str
    lead_day: int
    regions: list[dict]

class RegionInfo(BaseModel):
    key: str
    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    region_type: str
    climate_zone: str
    lat_center: float
    lon_center: float

class ModelInfo(BaseModel):
    model_type: str
    evaluation: Optional[dict]
    feature_count: Optional[int]
    training_period: Optional[str]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "model_loaded": MODEL is not None,
        "feature_store_loaded": FEATURE_DF is not None,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/regions", response_model=list[RegionInfo], tags=["Data"])
def list_regions():
    """Return all IMD subdivisions with their bounding boxes."""
    regions = []
    for key, meta in IMD_SUBDIVISIONS.items():
        regions.append(RegionInfo(
            key=key,
            name=meta["name"],
            lat_min=meta["lat_min"],
            lat_max=meta["lat_max"],
            lon_min=meta["lon_min"],
            lon_max=meta["lon_max"],
            region_type=meta["region_type"],
            climate_zone=meta["climate_zone"],
            lat_center=(meta["lat_min"] + meta["lat_max"]) / 2,
            lon_center=(meta["lon_min"] + meta["lon_max"]) / 2,
        ))
    return regions


@app.post("/forecast-confidence", response_model=ConfidenceResponse, tags=["Inference"])
def get_forecast_confidence(req: ConfidenceRequest):
    """
    Main inference endpoint.
    Returns bust probability, confidence score, and SHAP-based explanation
    for a specific (region, date, lead_day) combination.
    """
    if req.region not in IMD_SUBDIVISIONS:
        raise HTTPException(404, f"Region '{req.region}' not found. See GET /regions.")

    try:
        init_date = pd.Timestamp(req.date)
    except Exception:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

    region_meta = IMD_SUBDIVISIONS[req.region]
    result = _get_prediction(req.region, init_date, req.lead_day)

    return ConfidenceResponse(
        region=req.region,
        region_name=region_meta["name"],
        date=req.date,
        lead_day=req.lead_day,
        **result,
    )


@app.get("/forecast-confidence/{region}", tags=["Inference"])
def get_region_all_lead_days(
    region: str,
    date: str = Query(..., description="Init date YYYY-MM-DD"),
):
    """
    Returns confidence scores for all lead days (1–10) for one region.
    Used for the confidence-convergence time-series chart in the dashboard.
    """
    if region not in IMD_SUBDIVISIONS:
        raise HTTPException(404, f"Region '{region}' not found.")

    try:
        init_date = pd.Timestamp(date)
    except Exception:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

    results = []
    for lead_day in range(1, 11):
        prediction = _get_prediction(region, init_date, lead_day)
        results.append({
            "lead_day": lead_day,
            "valid_date": (init_date + pd.Timedelta(days=lead_day)).strftime("%Y-%m-%d"),
            "bust_probability": prediction["bust_probability"],
            "confidence": prediction["confidence"],
            "confidence_label": prediction["confidence_label"],
            "confidence_color": prediction["confidence_color"],
            "summary": prediction["summary"],
        })

    return {
        "region": region,
        "region_name": IMD_SUBDIVISIONS[region]["name"],
        "date": date,
        "lead_days": results,
    }


@app.get("/confidence-map/{date}", response_model=RegionConfidenceMap, tags=["Inference"])
def get_confidence_map(
    date: str,
    lead_day: int = Query(3, ge=1, le=10, description="Lead day for the map"),
    regions: Optional[str] = Query(None, description="Comma-separated region keys (default: all pilot regions)"),
):
    """
    Returns confidence scores for all regions on one date at one lead day.
    Powers the choropleth map in the dashboard.
    """
    try:
        init_date = pd.Timestamp(date)
    except Exception:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

    region_keys = regions.split(",") if regions else PILOT_REGIONS
    region_keys = [r.strip().upper() for r in region_keys if r.strip().upper() in IMD_SUBDIVISIONS]

    if not region_keys:
        raise HTTPException(400, "No valid regions specified.")

    map_data = []
    for region_key in region_keys:
        meta = IMD_SUBDIVISIONS[region_key]
        prediction = _get_prediction(region_key, init_date, lead_day)
        map_data.append({
            "region": region_key,
            "name": meta["name"],
            "lat_center": (meta["lat_min"] + meta["lat_max"]) / 2,
            "lon_center": (meta["lon_min"] + meta["lon_max"]) / 2,
            "lat_min": meta["lat_min"],
            "lat_max": meta["lat_max"],
            "lon_min": meta["lon_min"],
            "lon_max": meta["lon_max"],
            "bust_probability": prediction["bust_probability"],
            "confidence": prediction["confidence"],
            "confidence_label": prediction["confidence_label"],
            "confidence_color": prediction["confidence_color"],
            "summary": prediction["summary"],
        })

    return RegionConfidenceMap(date=date, lead_day=lead_day, regions=map_data)


@app.get("/bust-events", tags=["Data"])
def get_known_bust_events():
    """Returns the curated list of real historical bust events used for demo scenarios."""
    return {"bust_events": KNOWN_BUST_EVENTS}


@app.get("/model-info", response_model=ModelInfo, tags=["System"])
def get_model_info():
    """Model metadata and evaluation metrics."""
    feature_count = None
    if FEATURE_DF is not None:
        X, _ = FeatureEngineer().get_feature_matrix(FEATURE_DF)
        feature_count = len(X.columns)

    return ModelInfo(
        model_type="Ensemble (XGBoost + LightGBM) with Platt calibration",
        evaluation=EVAL_RESULTS,
        feature_count=feature_count,
        training_period="Jun 2021 – Sep 2022 (train) | Oct 2022 – May 2023 (val) | Jun–Sep 2023 (test)",
    )


# ── Prediction helpers ────────────────────────────────────────────────────────

def _get_prediction(region: str, init_date: pd.Timestamp, lead_day: int) -> dict:
    """
    Routes to real inference if the model + feature store are available,
    otherwise falls back to deterministic mock output (demo/dev mode).
    """
    if MODEL is not None and FEATURE_DF is not None:
        try:
            return _real_prediction(region, init_date, lead_day)
        except Exception as e:
            logger.warning(f"Real prediction failed, using mock: {e}")

    return _mock_prediction(region, init_date, lead_day)


def _real_prediction(region: str, init_date: pd.Timestamp, lead_day: int) -> dict:
    """Look up feature row from the store and run inference + SHAP explanation."""
    row = FEATURE_DF[
        (FEATURE_DF["region"] == region) &
        (FEATURE_DF["init_date"].dt.date == init_date.date()) &
        (FEATURE_DF["lead_day"] == lead_day)
    ]

    if row.empty:
        raise ValueError(f"No feature data for {region} {init_date.date()} D+{lead_day}")

    X, _ = FEATURE_ENGINEER.get_feature_matrix(row)
    return explain_single_prediction(MODEL, X, list(X.columns))


def _mock_prediction(region: str, init_date: pd.Timestamp, lead_day: int) -> dict:
    """
    Deterministic mock for dev/demo when model isn't trained yet.
    Seeds from (region, date, lead_day) so repeated calls return the same value.
    Known bust events get elevated bust probability.
    """
    seed = hash(f"{region}{init_date.date()}{lead_day}") % 10000
    rng = np.random.RandomState(seed)

    is_known_bust = any(
        e["region"] == region and abs((pd.Timestamp(e["date"]) - init_date).days) <= 1
        for e in KNOWN_BUST_EVENTS
    )

    if is_known_bust:
        bust_prob = 0.65 + 0.2 * (lead_day / 10) + rng.uniform(-0.05, 0.05)
    else:
        base = 0.12 + 0.04 * lead_day
        bust_prob = min(max(base + rng.uniform(-0.05, 0.05), 0.05), 0.95)

    confidence = 1.0 - bust_prob
    mock_phrases = _mock_phrases(bust_prob, lead_day, rng)

    summary = EXPLAINABILITY_ENGINE._assemble_summary(confidence, mock_phrases, bust_prob)
    advisory = EXPLAINABILITY_ENGINE._generate_advisory(confidence, bust_prob)

    return {
        "bust_probability": round(float(bust_prob), 3),
        "confidence": round(float(confidence), 3),
        "confidence_label": _confidence_label(confidence),
        "confidence_color": _confidence_color(confidence),
        "summary": f"[DEMO] {summary}",
        "detail": "Mock prediction — model not yet trained.",
        "advisory": advisory,
        "top_factors": [],
        "data_source": "Mock data (model training in progress)",
    }


def _mock_phrases(bust_prob: float, lead_day: int, rng: np.random.RandomState) -> list[str]:
    """Sample explanation phrases for demo mode."""
    all_phrases = [
        f"the long lead time of this forecast (Day {lead_day})",
        "elevated low-level wind speeds suggesting an active monsoon surge",
        "an unusually large 24-hour forecast change in rainfall",
        "a historically high bust frequency for this region and season",
        "a sharp pressure gradient indicating a fast-evolving system",
        "similar past synoptic patterns that frequently led to forecast busts",
    ]
    n = 3 if bust_prob > 0.5 else 2
    indices = rng.choice(len(all_phrases), size=n, replace=False)
    return [all_phrases[i] for i in sorted(indices)]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
