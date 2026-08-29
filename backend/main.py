from datetime import date
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from model_utils import predict_real, real_model_available

app = FastAPI(
    title="Forecast Bust Detection API",
    description=(
        "Serves region-wise forecast-bust probability, confidence score, and a "
        "plain-English explanation for medium-range (Day 1-10) NWP forecasts. "
        "Backed by a mock model until P4's real model is wired in on Day 3."
    ),
    version="0.2.0",
)

# Allow the Vite dev server (P1's frontend) to call this API during development.
# Tighten this list before deployment (Day 6).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)


class ForecastConfidenceResponse(BaseModel):
    region: str
    date: date
    lead_day: int
    bust_probability: float = Field(..., ge=0.0, le=1.0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    explanation_text: str
    top_factors: list[str]
    is_mock: bool = Field(
        True, description="True until P4's real model + P3's real features are wired in."
    )


KNOWN_REGIONS = {
    "coastal-karnataka",
    "konkan-goa",
    "vidarbha",
    "west-rajasthan",
    "gangetic-west-bengal",
    "all-india",
}

_MOCK_SCENARIOS: dict[tuple[str, int], tuple[float, str, list[str]]] = {
    ("coastal-karnataka", 1): (
        0.08,
        "High confidence: forecast is stable with low run-to-run variation.",
        ["low ensemble spread", "minimal 24h forecast jump"],
    ),
    ("coastal-karnataka", 5): (
        0.42,
        "Moderate confidence: some disagreement building between recent forecast runs.",
        ["moderate run-to-run jump", "lead day 5 uncertainty growth"],
    ),
    ("konkan-goa", 6): (
        0.71,
        "Low confidence: signs consistent with an active monsoon low approaching the coast.",
        ["elevated ensemble spread", "sharp pressure gradient", "monsoon-low proxy flag"],
    ),
    ("west-rajasthan", 3): (
        0.15,
        "High confidence: dry synoptic pattern with historically low bust rate for this region/season.",
        ["low historical analogue bust-rate", "stable pressure field"],
    ),
    ("vidarbha", 8): (
        0.63,
        "Low confidence: long lead time combined with a documented history of forecast busts for this pattern type.",
        ["lead day 8 uncertainty", "high historical analogue bust-rate"],
    ),
}


def _mock_prediction(region: str, lead_day: int) -> tuple[float, str, list[str]]:
    """Return a scenario if we have one; otherwise synthesize a plausible mock value.

    Kept deterministic (seeded by region+lead_day) so re-running the same query
    during a live demo always returns the same number.
    """
    key = (region, lead_day)
    if key in _MOCK_SCENARIOS:
        return _MOCK_SCENARIOS[key]

    # Simple deterministic synth: uncertainty grows with lead day, capped at 0.85.
    base = 0.05 + (lead_day / 10) * 0.55
    bust_probability = round(min(base, 0.85), 2)
    explanation = (
        f"Placeholder confidence estimate for lead day {lead_day} "
        f"(no curated scenario for '{region}' yet — this will be replaced by "
        f"P4's real model output on Day 3)."
    )
    factors = ["lead-time uncertainty (mock)"]
    return bust_probability, explanation, factors


@app.get("/forecast-confidence", response_model=ForecastConfidenceResponse)
def get_forecast_confidence(
    region: str = Query(..., description="Region slug, e.g. 'coastal-karnataka'"),
    forecast_date: date = Query(..., alias="date", description="Forecast issue date, YYYY-MM-DD"),
    lead_day: int = Query(..., ge=1, le=10, description="Lead day, 1-10"),
):
    """
    Returns bust probability, a confidence score, and a plain-English explanation
    for the given region / forecast date / lead day.

    Day 1-2: values are mock/deterministic. Day 3 onward: this will load P4's
    trained model via joblib and call P3's feature pipeline for the real inputs —
    the response *shape* below should not change, so P1 and P4 can build against
    it starting today.
    """
    region_slug = region.lower().strip()
    if region_slug not in KNOWN_REGIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown region '{region}'. Known regions: {sorted(KNOWN_REGIONS)}",
        )

    bust_probability, explanation, factors = _mock_prediction(region_slug, lead_day)
    confidence_score = round(1.0 - bust_probability, 2)

    return ForecastConfidenceResponse(
        region=region_slug,
        date=forecast_date,
        lead_day=lead_day,
        bust_probability=bust_probability,
        confidence_score=confidence_score,
        explanation_text=explanation,
        top_factors=factors,
        is_mock=True,
    )


@app.get("/health")
def health_check():
    """Simple liveness check — useful for Docker/deployment smoke tests on Day 6."""
    return {"status": "ok"}
