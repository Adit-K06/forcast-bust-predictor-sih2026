# P2 — Data Pipeline

A robust data ingestion and preprocessing pipeline for aligning **ERA5 reanalysis observations** with **GFS weather forecasts** for precipitation forecasting across multiple Indian regions.

## Overview

The P2 data pipeline prepares physically consistent, ML-ready datasets by:

- Downloading **ERA5 reanalysis** data from Copernicus CDS as observed ground truth.
- Downloading **GFS forecasts** from AWS Open Data.
- Regridding GFS forecasts onto the ERA5 spatial grid using `xarray.interp()`.
- Aligning forecast and observed precipitation values.
- Converting precipitation units into consistent **millimeter (mm)** measurements.
- Running automated data-quality and physics validation.
- Producing Parquet datasets for downstream **ML (P3)** and **Baseline (P6)** pipelines.
- Providing a lightweight offline dataset for reliable live demonstrations.

---

## Pipeline Architecture

```text
                 ┌─────────────────────┐
                 │   ERA5 Reanalysis   │
                 │   Copernicus CDS    │
                 └──────────┬──────────┘
                            │
                            │ Observations
                            ▼
                    ┌───────────────┐
                    │ ERA5 Grid     │
                    │ Precipitation │
                    │     → mm      │
                    └───────┬───────┘
                            │
                            │
                            │ Alignment
                            ▼
┌────────────────┐   ┌───────────────┐
│ GFS Forecasts  │──▶│ Regridding    │
│ AWS Open Data  │   │ xarray.interp │
└────────────────┘   └───────┬───────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Aligned Dataset  │
                    │ Forecast vs Obs  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ QA Validation    │
                    │ qa_pass.py       │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Parquet Dataset  │
                    │ ML / Baseline    │
                    └──────────────────┘
```

---

# Development Timeline

## Day 1 — Data Access & Initial Architecture

- Verified programmatic access to **ERA5 reanalysis** through Copernicus CDS.
- Verified access to **GFS forecasts** through AWS Open Data.
- Established the initial ingestion architecture.
- Downloaded pilot data for **Coastal Karnataka**.

---

## Day 2 — Pilot Alignment Pipeline

### Coverage

| Parameter | Value |
|---|---|
| Period | July 1–14, 2023 |
| Duration | 14 days |
| Region | Coastal Karnataka |
| GFS Resolution | 0.25° |

### Implementation

GFS forecasts were regridded onto the ERA5 observation grid using:

```python
xarray.interp(..., method="linear")
```

This ensured that forecast and observed precipitation values were spatially aligned before comparison.

### Output

```text
Rows:       17,836
Columns:    7
Date range: 20230701 → 20230714
Region:     Coastal Karnataka
```

### Files

```text
data-pipeline/
├── download_pilot.py
└── ingest.py
```

The resulting `aligned_pilot.parquet` dataset was used to unblock the downstream ML and baseline teams.

---

# Day 3 — Production Pipeline

The pipeline was scaled from the pilot dataset to the complete **2023 monsoon season**.

### Coverage

- Period: **June 1 – September 30, 2023**
- Duration: **122 days**
- Regions:
  - Coastal Karnataka
  - Maharashtra
  - Tamil Nadu
- GFS forecast lead time: **f024 / lead_day=1**
- Observation variable: **Total precipitation**

### Production Files

```text
data-pipeline/
├── download_full.py
├── ingest_full.py
└── requirements-day3.txt
```

### Final Dataset

```text
Total rows: 6,013,136
Date range: 20230601 → 20230930
Columns:    7
```

### Regional Distribution

```text
Coastal Karnataka : 1,354,444
Maharashtra       : 2,947,032
Tamil Nadu        : 1,711,660
--------------------------------
Total             : 6,013,136
```

The production pipeline includes error handling and resume behavior so individual network or file failures do not terminate the complete dataset build.

---

# Day 4 — QA & Physics Validation

An automated QA script was introduced to validate the production dataset.

### QA Script

```text
qa_pass.py
```

The validation process checks:

- Data types
- Missing values
- Date completeness
- Forecast/observation ranges
- Physical plausibility
- Dataset structure

### Critical Issue Identified

The initial GFS extraction selected an incorrect variable, resulting in atmospheric pressure values instead of precipitation.

At the same time, ERA5 precipitation was stored in **meters**, while the ML pipeline expected precipitation in **millimeters**.

### Fixes Applied

#### GFS

The extraction was restricted to surface accumulated precipitation:

```python
filter_by_keys={
    'typeOfLevel': 'surface',
    'stepType': 'accum'
}
```

#### ERA5

Total precipitation was converted from meters to millimeters:

```python
tp_mm = tp * 1000.0
```

### Final QA Values

```text
Maximum Forecast Precipitation : 160.4 mm
Maximum Observed Precipitation : 17.7 mm
```

The resulting dataset is physically consistent and suitable for downstream ML training.

---

# Day 5 & Day 6 — Offline Demo Dataset

To ensure that the live pitch did not depend on external APIs or network availability, a targeted historical extraction workflow was developed.

### Purpose

Instead of downloading the complete production dataset during the demonstration, the pipeline extracts a small set of predefined historical case studies.

### Coverage

**Historical dates:** 5 specific cases from 2021–2023

**Regions:**

- Odisha
- Kerala
- Uttarakhand
- Vidarbha
- Andhra Pradesh Coast

### Files

```text
data-pipeline/
├── download_demo.py
├── ingest_demo.py
└── output/
    └── demo_data_offline.parquet
```

### Final Dataset

```text
Rows:    7,940
Columns: 7
```

The offline dataset provides a lightweight and physically accurate data source for the live judging/demo interface without requiring real-time API access.

---

# Reliability & Engineering Fixes

## 1. ERA5 Duplicate-Day Request

### Problem

The CDS API rejected full-season requests with:

```text
request['day']: has repeated values in the list
```

### Solution

ERA5 data is downloaded **month-by-month** and subsequently combined into region-specific datasets.

---

## 2. Windows Unicode Logging

### Problem

Windows `cp1252` console encoding caused:

```text
UnicodeEncodeError
```

when logging special status symbols.

### Solution

Production logs use UTF-8, while console status messages use ASCII-safe labels:

```text
[OK]
[WARN]
[ERROR]
```

---

## 3. Incomplete / Corrupted GFS Files

### Problem

Interrupted downloads could produce truncated GRIB files and errors such as:

```text
PrematureEndOfFileError
```

### Solution

Individual file-processing failures are handled using `try/except`.

Successful and skipped files are recorded in the logs without terminating the entire pipeline.

---

## 4. AWS DNS / Network Failures

### Problem

Temporary AWS DNS failures produced errors such as:

```text
getaddrinfo failed
```

### Solution

The downloader:

- Continues after individual download failures.
- Checks whether files already exist.
- Can be safely re-run.
- Recovers missing files on subsequent runs.

This provides basic **resume/recovery behavior**.

---

## 5. Efficient GFS Downloading

### Problem

Downloading the same global GFS source file separately for every region would unnecessarily increase bandwidth and processing time.

### Solution

Each daily GFS source file is downloaded once and then mapped locally to the required regions.

---

# Key Design Decisions

## Regridding

GFS has a **0.25° spatial resolution**, while the observation grid differs.

To make forecast and observed precipitation directly comparable, GFS is interpolated onto the ERA5 grid:

```python
gfs.interp(
    latitude=era5.latitude,
    longitude=era5.longitude,
    method="linear"
)
```

This ensures both datasets share a common spatial coordinate system.

---

## Precipitation Variables

### ERA5

```text
Variable: total precipitation (tp)
Original unit: meters
Final unit: millimeters
```

Conversion:

```python
tp_mm = tp * 1000.0
```

### GFS

```text
Variable: surface accumulated precipitation
Final datatype: float64
```

The GFS extraction specifically targets surface accumulated precipitation rather than atmospheric pressure variables.

---

# Multi-Region Architecture

Regions are centrally configured so additional geographic regions can be added without redesigning the pipeline.

Conceptually:

```python
REGIONS = {
    "coastal_karnataka": {...},
    "maharashtra": {...},
    "tamil_nadu": {...}
}
```

This makes the pipeline extensible for additional IMD subdivisions or other geographic areas.

---

# Repository Structure

```text
ocs/
├── contributions/
│   └── P2.md
│
└── data-pipeline/
    ├── download_pilot.py
    ├── ingest.py
    ├── download_full.py
    ├── ingest_full.py
    ├── download_demo.py
    ├── ingest_demo.py
    ├── qa_pass.py
    │
    ├── requirements.txt
    ├── requirements-day3.txt
    ├── README.md
    │
    └── output/
        ├── aligned_pilot.parquet
        └── demo_data_offline.parquet
```

---

# Running the Pipeline

## 1. Production Dataset

### Download source data

```powershell
python data-pipeline/download_full.py
```

### Build aligned dataset

```powershell
python data-pipeline/ingest_full.py
```

### Run QA validation

```powershell
python data-pipeline/qa_pass.py
```

---

## 2. Offline Demo Dataset

### Download targeted historical data

```powershell
python data-pipeline/download_demo.py
```

### Build the demo dataset

```powershell
python data-pipeline/ingest_demo.py
```

The resulting dataset is:

```text
data-pipeline/output/demo_data_offline.parquet
```

---

# Output Summary

| Dataset | Period | Regions | Rows |
|---|---|---|---:|
| Pilot | Jul 1–14, 2023 | Coastal Karnataka | 17,836 |
| Production | Jun 1–Sep 30, 2023 | 3 regions | 6,013,136 |
| Offline Demo | 2021–2023 cases | 5 regions | 7,940 |

All final precipitation values are represented in **millimeters (mm)** and use compatible numeric datatypes for downstream ML processing.

---

# Downstream Consumers

The P2 pipeline provides datasets for:

```text
P2 — Data Pipeline
        │
        ├───────────────┐
        ▼               ▼
   P3 — ML         P6 — Baseline
        │               │
        └───────┬───────┘
                ▼
          Forecasting UI
             / Demo
```

The primary goal of P2 is to ensure that downstream teams receive **clean, aligned, physically valid, and reproducible data**.

---

# Final Deliverables

### Production

```text
6,013,136 rows
122 days
3 regions
7 columns
```

### Offline Demo

```text
7,940 rows
5 historical regional case studies
7 columns
```

### Core Capabilities

- ERA5 ingestion
- GFS ingestion
- Spatial regridding
- Forecast/observation alignment
- Unit normalization
- Automated QA
- Error handling
- Resume/recovery behavior
- Multi-region processing
- Offline demo extraction
- Parquet dataset generation

---

## Status

**P2 Data Pipeline — Completed through Day 6**

The pipeline successfully produces ML-ready precipitation datasets while remaining resilient to API limitations, network failures, corrupted source files, datatype mismatches, and physical unit inconsistencies.