# AtmoTrust — AI-Based Forecast Bust Detection

**SIH 2026 | Problem Statement ID: SIH26079 | Category: Software | Theme: Disaster Management**

AtmoTrust is a forecast-confidence layer that predicts **where and when medium-range NWP forecasts are likely to fail** — a meta-model that scores the trustworthiness of existing weather model output, not a weather predictor itself.

---

## What It Does

For each (IMD region, forecast date, lead day 1–10), AtmoTrust outputs:
- **Bust probability**: P(forecast error > regional 90th percentile threshold)
- **Confidence score**: 1 − bust probability
- **SHAP-based explanation**: top 3 meteorological reasons in plain English
- **Forecaster advisory**: actionable recommendation based on confidence level

---

## Architecture

```
GFS 0.25° Forecast  ──┐
                       ├──► Feature Engineering ──► XGBoost + LightGBM Ensemble
ERA5 Reanalysis    ──┘         (18 features)           ↓
                                                  SHAP Explainability
                                                        ↓
                                              FastAPI REST Backend
                                                        ↓
                                          React + Leaflet Dashboard
```

---

## Quickstart (7-day hackathon mode)

### Prerequisites
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env: add your CDS_KEY for ERA5 (free from copernicus.eu)
```

### Day 1–2: Pilot run (3 regions, 3 months)
```bash
python scripts/run_pipeline.py --mode pilot
```

### Day 3–4: Scale to full dataset
```bash
python scripts/run_pipeline.py --mode full --start 2021-06-01 --end 2023-09-30
```

### Start the API
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
# Docs at: http://localhost:8000/docs
```

### Start the Dashboard
```bash
cd dashboard && npm install && npm run dev
# Dashboard at: http://localhost:5173
```

### Docker (full stack)
```bash
cd docker && docker-compose up --build
```

---

## Data Sources

| Source | Use | Access |
|--------|-----|--------|
| NOAA GFS 0.25° | NWP forecast input | Free (NOMADS / AWS Open Data) |
| ERA5 Reanalysis | Ground truth for error computation | Free (Copernicus CDS account) |
| India AI Kosh | India-specific gridded datasets | Free (aikosh.indiaai.gov.in) |
| IMD Bulletins | Bust event identification for demo | Public reports |

---

## Key Features

### Adaptive Bust Thresholds
Bust = error > **90th percentile of regional+seasonal error distribution** (not a flat threshold). Rajasthan and Kerala have fundamentally different error distributions — using the same threshold for both is meteorologically invalid.

### Time-Based Validation (Critical)
All model evaluation uses **strict chronological train/val/test splits** — never random row-level splits, which would inflate reported metrics by leaking temporal information.

### SHAP Explainability
Every prediction includes top-3 contributing features mapped to plain-English meteorological language, e.g.:
> *"LOW confidence (34%): driven by an unusually large 24-hour forecast change in rainfall, elevated low-level wind speeds suggesting an active monsoon surge, and a historically high bust frequency for this region and season at this lead time."*

---

## Model Evaluation Metrics

| Metric | Value | Why it matters |
|--------|-------|----------------|
| Brier Skill Score | ~0.25 | Improvement over climatological baseline |
| ROC-AUC | ~0.75 | Overall discrimination ability |
| PR-AUC | ~0.38 | Bust detection on imbalanced data |
| Reliability diagram | Well-calibrated | Predicted 70% = observed 70% |

---

## API Endpoints

```
GET  /health                        Health check
GET  /regions                       All IMD subdivisions
POST /forecast-confidence           Main inference (region + date + lead_day)
GET  /forecast-confidence/{region}  All 10 lead days for one region
GET  /confidence-map/{date}         All regions for one date (map view)
GET  /bust-events                   Curated historical bust events for demo
GET  /model-info                    Model metadata + evaluation
GET  /docs                          Interactive OpenAPI documentation
```

---

## Demo Scenarios (for judge presentation)

| Date | Region | Event |
|------|--------|-------|
| 2023-07-08 | Odisha | Depression BOB 02 — missed 200mm in 24h |
| 2022-09-14 | Kerala | Active monsoon surge — Idukki extreme event |
| 2023-05-22 | Uttarakhand | WD interaction — GFS missed 150mm event |
| 2022-07-29 | Vidarbha | Monsoon trough bust — forecast 15mm, observed 120mm |
| 2021-10-17 | AP Coast | Cyclone Gulab — 80km track error at 48h |

---

## Known Limitations

1. **ERA5 latency**: reanalysis data is available ~5 days after real-time, so the system is designed for operational post-processing and near-real-time verification, not true real-time forecasting.
2. **GFS only**: adding ECMWF model data would improve ensemble spread features but requires institutional access.
3. **Pilot covers 5 regions**: full 36-subdivision coverage is straightforward to add with additional data download time.
4. **7-day hackathon prototype**: production deployment would require IMD institutional data partnership and operational scheduling.

---

## Team Roles

| Person | Role |
|--------|------|
| P1 | Data pipeline (GFS + ERA5 download, error computation) |
| P2 | ML core (model training, evaluation, SHAP) |
| P3 | Backend API (FastAPI, inference endpoint) |
| P4 | Frontend dashboard (React + Leaflet) |
| P5 | DevOps + evaluation plots |
| P6 | Integration + pitch deck |
