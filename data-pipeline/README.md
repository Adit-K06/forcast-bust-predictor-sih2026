# P2 Data Pipeline — Till Day 3

## Overview

The pipeline:

- Downloads **ERA5 reanalysis** as observed ground truth.
- Downloads **GFS forecasts** from AWS Open Data.
- Regrids GFS onto the ERA5 grid using `xarray.interp()`.
- Aligns forecast and observed precipitation values.
- Produces a Parquet dataset for P3 (ML) and P6 (Baseline).
- Includes logging, retry/resume behavior, and graceful handling of incomplete files.

---

## What Was Delivered

### Day 2 — Pilot Pipeline

**Coverage**

- Period: **July 1–14, 2023**
- Region: **Coastal Karnataka**
- Duration: **14 days**

**Files**

```text
data-pipeline/
├── download_pilot.py
└── ingest.py
```

**Workflow**

```text
ERA5 observations
       +
GFS forecasts
       ↓
GFS → ERA5 regridding
       ↓
Forecast/observation alignment
       ↓
aligned_pilot.parquet
```

**Actual result**

```text
Rows:       17,836
Columns:    7
Date range: 20230701 → 20230714
Region:     Coastal Karnataka
```

Schema:

```text
latitude
longitude
region
date
lead_day
forecast_value
observed_value
```

---

### Day 3 — Production Pipeline

**Coverage**

- Period: **June 1 – September 30, 2023**
- Duration: **122 days**
- Regions:
  - Coastal Karnataka
  - Maharashtra
  - Tamil Nadu
- GFS forecast: **lead time f024 / lead_day=1**
- Observation variable: **total precipitation**

**Files**

```text
data-pipeline/
├── download_full.py
├── ingest_full.py
└── requirements-day3.txt
```

**Workflow**

```text
                    DAY 3
                      │
          ┌───────────┴───────────┐
          │                       │
        ERA5                     GFS
          │                       │
   Regional ground truth    Daily forecasts
          │                       │
          └───────────┬───────────┘
                      ↓
            GFS → ERA5 regridding
                      ↓
           Forecast/observation merge
                      ↓
              Multi-region dataset
                      ↓
              Parquet dataset
```

**Actual result**

```text
Total rows: 6,013,136
Date range: 20230601 → 20230930
Regions:    Coastal Karnataka, Maharashtra, Tamil Nadu
Columns:    7
```

Regional totals:

```text
Coastal Karnataka : 1,354,444
Maharashtra       : 2,947,032
Tamil Nadu        : 1,711,660
--------------------------------
Total             : 6,013,136
```

Final schema:

```text
latitude
longitude
region
date
lead_day
forecast_value
observed_value
```

> Note: the current production script writes the final dataset to `data-pipeline/output/aligned_pilot.parquet`. The filename is retained for compatibility with the existing pipeline, but the Day 3 contents are the full production dataset.

---

## Reliability Fixes Applied

### 1. ERA5 duplicate-day request

**Problem**

The original full-season CDS request supplied multiple months together with repeated day values. For example, `01` appeared once for June, once for July, once for August, and once for September.

The CDS API rejected the request with:

```text
request['day']: has repeated values in the list
```

**Fix**

ERA5 is downloaded **month-by-month**:

```text
June
July
August
September
```

The monthly files are then combined into the region-specific ERA5 files used by the ingestion pipeline.

---

### 2. Windows Unicode logging

**Problem**

Windows `cp1252` console encoding could not represent symbols such as:

```text
✓  ✗  ⚠  →
```

This produced:

```text
UnicodeEncodeError: 'charmap' codec can't encode character
```

**Fix**

Production logging uses UTF-8 for the log file and ASCII status labels:

```text
[OK]
[ERROR]
[WARN]
-->
```

---

### 3. Incomplete / corrupted GFS files

**Problem**

Interrupted downloads can create truncated GRIB files. `cfgrib` may then report:

```text
PrematureEndOfFileError:
End of resource reached when reading message
```

**Fix**

The ingestion pipeline handles individual file-processing failures without terminating the complete run. Successful and failed/skipped files are tracked in the logs.

When a download is incomplete, the downloader can be run again to recover the missing file.

---

### 4. AWS DNS / network failures

**Problem**

Some GFS requests temporarily failed with:

```text
getaddrinfo failed
```

This indicates a DNS/network resolution failure while connecting to the AWS GFS endpoint.

**Fix**

The downloader continues after individual failures and supports re-running to recover missing dates. Failed dates were successfully recovered during the Day 3 run.

---

### 5. Efficient GFS handling

GFS is a global forecast product. The downloader retrieves each daily source file once and creates region-specific links/files for the filenames expected by `ingest_full.py`.

This avoids downloading identical global GFS data separately for every region.

---

## Key Design Decisions

### Regridding

GFS data is regridded to the ERA5 grid using:

```python
xarray.interp(..., method="linear")
```

This allows forecast and observation values to be compared on the same spatial grid.

### Variables

The pipeline uses:

- **ERA5:** total precipitation (`tp`)
- **GFS:** forecast data at the required GRIB level/filter

### Error handling

The Day 3 pipeline:

- Catches download errors.
- Continues when an individual day fails.
- Skips corrupted GRIB messages/files during ingestion.
- Reports success/failure counts.

### Logging

Logs are written to:

```text
data-pipeline/download.log
data-pipeline/ingest.log
```

and important status information is also printed to the console.

### Multi-region design

Regions are configured centrally so additional regions can be added later without redesigning the overall pipeline.

---

## Repository Files

The source/documentation files for P2 are:

```text
data-pipeline/
├── download_pilot.py
├── ingest.py
├── download_full.py
├── ingest_full.py
├── requirements.txt
├── requirements-day3.txt
├── README.md
└── output/
```


---

## Environment Setup

Windows uses Conda because `cfgrib` depends on native ecCodes libraries.

Create the environment:

```powershell
conda create -n forecast-p2 -c conda-forge python=3.11 xarray cfgrib eccodes pandas requests netcdf4 cdsapi pyarrow scipy -y
```

Activate:

```powershell
conda activate forecast-p2
```

For ERA5 access, configure the required CDS API credentials in the user's home directory.

---

## Running Day 2

Download the pilot data:

```powershell
python data-pipeline/download_pilot.py
```

Process and align it:

```powershell
python data-pipeline/ingest.py
```

Check the output:

```powershell
Get-ChildItem data-pipeline/output
```

---

## Running Day 3

Download the production data:

```powershell
python data-pipeline/download_full.py
```

Then align all regions:

```powershell
python data-pipeline/ingest_full.py
```

Check the logs:

```powershell
Get-Content data-pipeline/download.log
Get-Content data-pipeline/ingest.log
```

---

## Validation

Validate the Parquet dataset with pandas:

```powershell
python -c "import pandas as pd; df=pd.read_parquet('data-pipeline/output/aligned_pilot.parquet'); print('Shape:', df.shape); print('Columns:', list(df.columns)); print('Date range:', df['date'].min(), 'to', df['date'].max()); print('Regions:', df['region'].unique()); print('Nulls:'); print(df.isna().sum())"
```

For the completed Day 3 run, the observed production values were:

```text
Shape:      (6013136, 7)
Date range: 20230601 to 20230930
Regions:    Coastal Karnataka, Maharashtra, Tamil Nadu
```

---

## Handoff to P3 — ML Team

The aligned dataset contains:

```text
latitude
longitude
region
date
lead_day
forecast_value
observed_value
```

It is ready for:

- Feature engineering
- Forecast-error analysis
- Bias correction
- Deep-learning model training
- Lead-time experiments

Suggested split for baseline/ML evaluation should keep forecast and observation pairs aligned by date and location.

---

## Handoff to P6 — Baseline Team

Use the same aligned dataset as P3 so that the baseline and ML model are evaluated on identical forecast/observation pairs.

Possible deterministic baselines include:

```text
Persistence
Climatology
NWP bias correction
```

Suggested metrics:

```text
RMSE
MAE
Correlation
```

---

## Next Steps

1. Validate the production dataset with P3 and P6.
2. Decide whether additional forecast lead times are required.
3. Add additional weather variables if requested by the ML team.
4. Monitor CDS API and AWS access limits during future data expansion.
5. Archive the generated dataset outside Git for reproducibility.

Potential future GFS lead times include:

```text
f024
f048
f072
...
```

---

## Support / Troubleshooting

### Environment problems

Check:

- Conda environment activation
- `cfgrib` / ecCodes installation
- SciPy installation
- CDS API credentials

Test the environment:

```powershell
python -c "import xarray, cfgrib, scipy, pandas; print('Environment OK')"
```

### Download problems

Check:

- Internet connection
- CDS API status/quota
- AWS S3 connectivity
- `data-pipeline/download.log`

For temporary GFS failures, re-run the downloader to recover missing dates.

### Alignment problems

Check:

- GRIB file integrity
- Latitude/longitude grids
- Missing values / NaNs
- `data-pipeline/ingest.log`

---

## Completion Status

### Day 2

```text
[OK] 14-day ERA5 pilot downloaded
[OK] 14-day GFS pilot downloaded
[OK] GFS regridded to ERA5 grid
[OK] Forecast/observation pairs generated
[OK] Pilot Parquet created
```

### Day 3

```text
[OK] 122-day monsoon period downloaded
[OK] 3 regions processed
[OK] ERA5 observations available
[OK] GFS forecasts available
[OK] GFS regridding completed
[OK] Corrupt/incomplete files handled
[OK] Production Parquet created
[OK] Dataset ready for P3 and P6
```
