# AtmoTrust — AI-Powered Forecast Bust Detection System

**Smart India Hackathon (SIH) 2026 | Problem Statement: SIH26079 | Theme: Disaster Management**

---

## 📌 Executive Summary

Numerical Weather Prediction (NWP) models (e.g. NOAA GFS, ECMWF) are indispensable for operational meteorology, yet medium-range forecasts (Day 1–10) occasionally experience catastrophic failures or **"forecast busts"** during rapidly evolving systems (monsoon depressions, western disturbances, extreme convective rainfall, cyclones, and monsoon breaks).

**AtmoTrust** is an operational meta-model layer that continuously monitors NWP model outputs, historical forecast error distributions, and atmospheric instability indicators to:
1. **Predict the probability of a forecast bust** (defined as forecast error exceeding the regional 90th percentile threshold).
2. **Assign a calibrated Confidence Score** (Day 1 to Day 10).
3. **Detect error-prone regions** with interactive spatial risk heatmaps.
4. **Deliver explainable meteorological rationales** (using SHAP TreeExplainer translated into plain English).
5. **Issue actionable forecaster advisories** for operational disaster management teams.

---

## 🏗️ System Architecture

```
                                  DATA SOURCES
                    ┌───────────────────────────────────────┐
                    │ NOAA GFS (0.25°) │ ERA5 Reanalysis   │
                    │ India AI Kosh    │ IMD Bulletins     │
                    └───────────────────┬───────────────────┘
                                        │
                                        ▼
                                 data_pipeline/
                  Ingestion, spatial alignment, & error computation
                                        │
                                        ▼
                                    features/
           Feature engineering (run jumps, cyclical dates, historical bust rates)
                                        │
                                        ▼
                                    ml_core/
             RandomForestClassifier (scikit-learn) trained on 6M+ grid rows
                                        │
                                        ▼
                    backend/ (FastAPI) + explainability/ (SHAP)
           REST Endpoints, TreeExplainer, plain-English translation & advisories
                                        │
                                        ▼
                                frontend/ (Vite + React)
            Interactive Leaflet Map, 10-Day Outlook Chart, Historical Busts UI
```

---

## 🔬 Model & Validation Details

- **Model Type:** `RandomForestClassifier` (100 estimators, random_state=42)
- **Features Analyzed:** `forecast_value` (precipitation mm), `hist_bust_rate`, `lead_day`, `month_sin`, `month_cos`, `precip_intensity_cat`, `region`, `season`
- **Validation Strategy:** Chronological split (70% train, 15% validation, 15% test) to prevent time-series data leakage.
- **Strict Leakage Prevention:** Verified removal of label-derived columns (`abs_error_mm`, `signed_error_mm`, `precip_observed_mm`, `bust_threshold_mm`).
- **Test Performance (985,760 samples):**
  - **ROC-AUC:** `0.971`
  - **PR-AUC:** `0.948`
  - **Brier Score:** `0.035`

### Honest Operational Scope
- **Real Model Coverage:** Trained on real NOAA GFS forecast grids and ERA5 observations covering Coastal Karnataka, Maharashtra, and Tamil Nadu during the active monsoon season (June–September 2023) at `lead_day = 1`.
- **Calibrated Fallback:** For out-of-scope dates, extended lead days (2–10), or additional regions, the system gracefully responds with a calibrated, deterministic meteorological mock, explicitly marked via `is_mock: true` in the API and badged in the UI.

---

## 🚀 Quickstart & Running the Project

### Prerequisites
- Python 3.10+
- Node.js 18+

### Option A: Standard Local Execution

#### 1. Start the FastAPI Backend
```bash
# From repository root:
python start_backend.py
```
*API will run at `http://127.0.0.1:8000` (Swagger interactive docs at `/docs`).*

#### 2. Start the React Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
*Open `http://localhost:5173` in your browser.*

---

### Option B: Docker Compose (One-Click Stack)
```bash
docker-compose up --build
```
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`

---

## 📡 Canonical API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/forecast-confidence` | Core inference: bust probability, confidence label, advisory & top SHAP factors |
| `GET` | `/10day-outlook` | Complete 10-day lead trajectory for a chosen region and date |
| `GET` | `/confidence-map/{date}` | Multi-region spatial confidence matrix for choropleth mapping |
| `GET` | `/bust-events` | Curated historical NWP bust cases for demonstration |
| `GET` | `/regions` | Supported IMD subdivisions and model coverage status |
| `GET` | `/model-info` | Real model loading status, test/validation metrics, and architecture info |
| `GET` | `/health` | Service liveness probe |

---

## 🎯 Demo Walkthrough Guide for Judges

1. **Live Real-Model Query:**
   - Select **Coastal Karnataka**, Date: `2023-07-15`, Lead Day: `Day 1`.
   - Result: Model badge displays **REAL MODEL** (`is_mock: false`), shows 96% bust risk with SHAP explanations citing heavy precipitation forecast and high historical bust frequency.
2. **10-Day Outlook Exploration:**
   - Observe how confidence degrades progressively from Day 1 to Day 10 across the dynamic bar chart. Click any day to update the detailed panel.
3. **Interactive Map Exploration:**
   - Explore the color-coded Leaflet choropleth map (Green: Low risk, Amber: Moderate risk, Red: High bust probability). Hover and click states to inspect regional reliability.
4. **Historical Forecast Busts Tab:**
   - Click the **Historical Busts** tab to inspect documented real-world NWP forecast failures (e.g. Depression BOB 02, Idukki monsoon surge, Western Disturbance in Uttarakhand) and drill into the regional analysis with one click.
5. **Model Info & Transparency Tab:**
   - View the **Model Info** tab showing live model loading status, training hyperparameters, validation scores, and full disclosure of scope.

---

## 👥 Team & Roles

- **P1 — Data Lead:** GFS & ERA5 data acquisition, spatial alignment & error computer
- **P2 — Feature Engineering:** Instability indicators, run jump computation, cyclical encodings
- **P3 — Machine Learning:** Model training, evaluation metrics, and hyperparameter tuning
- **P4 — Explainability:** SHAP TreeExplainer, meteorological dictionary, and plain-English translation
- **P5 — Backend & Deployment (Lead):** FastAPI architecture, model integration, CORS, Docker & full-stack integration
- **P6 — Integration & Pitch:** Presentation materials, documentation & user experience