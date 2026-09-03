# AtmoTrust - AI-Powered Forecast Bust Detection System

**Smart India Hackathon (SIH) 2026 | Problem Statement: SIH26079 | Theme: Disaster Management**

---

## 📌 Executive Summary

Numerical Weather Prediction (NWP) models (e.g. NOAA GFS, ECMWF) are indispensable for operational meteorology, yet medium-range forecasts (Day 1–10) occasionally experience catastrophic failures or **"forecast busts"**.

**AtmoTrust** is an operational meta-model layer that continuously monitors NWP model outputs and atmospheric instability indicators to:
1. **Predict forecast busts** before they happen.
2. **Deliver SHAP-powered explanations** to build forecaster trust.
3. **Provide 10-day confidence trajectories** to optimize disaster response planning.
4. **Evaluate performance rigorously** using WMO-standard Brier Skill Scores against climatology.
5. **Issue operational advisories** tailored for disaster management teams.

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

## 🔬 Core Features & Differentiators

### 1. SHAP Explainability in Real-Time
Black-box AI is unsuitable for operational meteorology. AtmoTrust integrates `shap.TreeExplainer` to extract the top contributing factors for every prediction, rendering them as dynamic, ranked progress bars so forecasters know exactly *why* a bust is likely.

### 2. "Bust Detection" Framing
Instead of predicting rainfall amounts, AtmoTrust predicts when the government's primary model (GFS) will be wrong. This addresses the hardest operational challenge: knowing when to override the model guidance.

### 3. WMO-Grade Evaluation (Brier Skill Score)
Accuracy and F1 scores are insufficient for meteorology. AtmoTrust evaluates its probability predictions using the Brier Skill Score (BSS). Our model achieves a **BSS of 0.817**, significantly outperforming naive climatological baselines.

### 4. 10-Day Lead Time Sweep
The dashboard features a dynamic 10-day confidence outlook. The interface calculates and color-codes the risk for the entire 10-day horizon, allowing teams to see exactly when confidence degrades.

### 5. Operational Advisories
When bust probabilities exceed 60%, the system automatically issues color-coded, actionable operational advisories to guide the meteorologist on duty.

---

## 🔬 Model & Validation Details

- **Model Type:** `RandomForestClassifier` (100 estimators, random_state=42)
- **Features Analyzed:** `forecast_value` (precipitation mm), `hist_bust_rate`, `lead_day`, `month_sin`, `month_cos`, `precip_intensity_cat`, `region`, `season`
- **Validation Strategy:** Chronological split (70% train, 15% validation, 15% test) to prevent time-series data leakage.
- **Strict Leakage Prevention:** Verified removal of label-derived columns (`abs_error_mm`, `signed_error_mm`, `precip_observed_mm`, `bust_threshold_mm`).
- **Test Performance (985,760 samples):**
  - **ROC-AUC:** `0.971`
  - **PR-AUC:** `0.948`
  - **Brier Skill Score (BSS):** `0.817` (Climatology baseline Brier Score: 0.191)

---

## 🚀 Quickstart & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+

### Option A: Standard Local Execution

#### 1. Start the FastAPI Backend
```bash
python start_backend.py
```
*API runs at `http://127.0.0.1:8000` (Swagger docs at `/docs`).*

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

## 📡 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/forecast-confidence` | Core inference: bust probability, advisory & SHAP factors |
| `GET` | `/10day-outlook` | 10-day lead trajectory for a chosen region and date |
| `GET` | `/confidence-map/{date}` | Spatial confidence matrix for choropleth mapping |
| `GET` | `/bust-events` | Curated historical NWP bust cases |
| `GET` | `/skill-score` | Brier Skill Score and climatology comparison metrics |
| `GET` | `/regions` | Supported IMD subdivisions |

---

## 🖥️ Usage

**Forecast Confidence Query**
Select any IMD subdivision from the dropdown, set a forecast date and lead day (1–10), and the system returns a calibrated bust probability along with the top contributing factors driving the prediction.

**10-Day Horizon**
The outlook chart plots the bust risk trajectory across all 10 lead days for the selected region and date. Clicking any day updates the main panel to reflect that specific lead time.

**Interactive Map**
The Leaflet choropleth map displays a colour-coded spatial risk overview across supported subdivisions. Clicking a state on the map navigates to its regional forecast panel.

**Historical Bust Events**
The Historical Busts tab contains documented real-world NWP forecast failures with observed vs. forecast rainfall figures. Selecting any event navigates directly to the corresponding regional forecast for that date and lead time.

**Model Transparency**
The Model Info tab exposes the full evaluation report — including Brier Skill Score vs. climatology, ROC-AUC, PR-AUC, and training data scope.

---

## 👥 Team & Roles

- **P1 — Data Lead:** GFS & ERA5 data acquisition, spatial alignment
- **P2 — Feature Engineering:** Instability indicators, run jump computation
- **P3 — Machine Learning:** Model training and evaluation
- **P4 — Explainability:** SHAP integration and meteorological dictionary
- **P5 — Backend:** FastAPI architecture and Docker integration
- **P6 — Frontend & Pitch:** React UI, UX design, and presentation