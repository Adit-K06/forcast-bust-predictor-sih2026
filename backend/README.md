# Backend — Forecast Bust Detection API

Owner: P5 (Backend, SHAP Explainability & Deployment — Steps 4, 5, 7)

## Run locally

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs to confirm the Swagger UI loads and to test the
endpoint manually with a few dummy query values.

## API contract 

### `GET /forecast-confidence`

**Query parameters**

| Param   | Type   | Required | Notes                                   |
|---------|--------|----------|------------------------------------------|
| region  | string | yes      | one of the known region slugs (see main.py `KNOWN_REGIONS`) |
| date    | string | yes      | `YYYY-MM-DD`, the forecast issue date    |
| lead_day| int    | yes      | 1-10                                      |

**Response body**

```json
{
  "region": "konkan-goa",
  "date": "2026-08-28",
  "lead_day": 6,
  "bust_probability": 0.71,
  "confidence_score": 0.29,
  "explanation_text": "Low confidence: signs consistent with an active monsoon low approaching the coast.",
  "top_factors": ["elevated ensemble spread", "sharp pressure gradient", "monsoon-low proxy flag"],
  "is_mock": true
}
```

`is_mock` will flip to `false` once P4's real model + P3's real features are wired in
(Day 3). Frontend (P1) and ML (P4) should both build against this exact shape starting
Day 1/2 so the Day 3 swap is a one-file change in `main.py`, not a rewrite on either side.

### `GET /health`

Liveness check. Returns `{"status": "ok"}`. Used for the Day 6 Docker smoke test.

## Known regions (Day 1-2 placeholder list)

`coastal-karnataka`, `konkan-goa`, `vidarbha`, `west-rajasthan`,
`gangetic-west-bengal`, `all-india`

This will be replaced with the final IMD-subdivision list once P2/P3 confirm the
spatial unit the feature pipeline actually uses (build guide Section 5.2).

## What's mock vs real right now

- Day 1-2: `bust_probability`, `confidence_score`, `explanation_text` are all
  hard-coded / deterministically synthesized in `main.py`. No model is loaded.
- Day 3: swap in `joblib.load("baseline_model.pkl")` (P4's model) + call P3's
  feature pipeline for the given region/date/lead_day.
- Day 4: replace the templated explanation text with real SHAP output.
