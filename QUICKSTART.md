# AtmoTrust — Quick Start Guide
**SIH 2026 | Problem Statement: SIH26079**

## Prerequisites
- Python 3.10+ (Anaconda recommended)
- Node.js 18+

---

## Run Locally (2 terminals)

### Terminal 1 — Backend API
```bash
cd forcast-bust-predictor-sih2026
pip install -r backend/requirements.txt
python start_backend.py
```
API runs at: **http://127.0.0.1:8000**
Swagger docs: **http://127.0.0.1:8000/docs**

### Terminal 2 — Frontend Dashboard
```bash
cd forcast-bust-predictor-sih2026/frontend
npm install
npm run dev
```
Dashboard at: **http://localhost:5173**

---

## Key Files

```
forcast-bust-predictor-sih2026/
├── backend/               FastAPI app (main.py, model_utils.py)
├── ml_core/               Trained model + evaluation
│   ├── model.joblib           RandomForest classifier (real, 6M rows)
│   ├── evaluation_results.json   ROC-AUC, PR-AUC, Brier metrics
│   ├── main.py                BustModelTrainer class
│   └── baseline_and_skill_score.py  BSS vs climatology (run to regenerate)
├── explainability/        SHAP TreeExplainer → plain English
├── features/
│   └── features.parquet   Real GFS + ERA5 features (50 MB, 6M rows)
├── data_pipeline/         GFS + ERA5 download and ingestion scripts
├── frontend/              React + Leaflet dashboard (Vite)
├── docs/contributions/    Per-member contribution logs (P1–P5)
├── Dockerfile             Backend container
├── docker-compose.yml     Full-stack container stack
└── start_backend.py       One-command backend launcher
```

---

## Evaluation Metrics (held-out test set, 901,971 samples)

| Metric | Baseline (Climatology) | AtmoTrust Model |
|---|---|---|
| Brier Score | 0.1963 | **0.0359** |
| ROC-AUC | 0.4579 | **0.9719** |
| PR-AUC | 0.2423 | **0.9509** |
| **Brier Skill Score** | — | **0.817** |

---

## Re-run Skill Score Evaluation
```bash
cd forcast-bust-predictor-sih2026
python ml_core/baseline_and_skill_score.py
# Output saved to ml_core/evaluation/
```
