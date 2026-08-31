
import pandas as pd

print("Running Day 4 QA Pass on demo_data_offline.parquet...")

df = pd.read_parquet('data-pipeline/output/demo_data_offline.parquet')

print("\n--- Data Types ---")
print(df.dtypes)

print("\n--- Missing Values (NaNs) ---")
print(df.isna().sum())

print("\n--- Outliers & Extremes ---")

if pd.api.types.is_numeric_dtype(df['forecast_value']):
    print("Negative Forecast Rain (Errors):", (df['forecast_value'] < 0).sum())
    print("Max Forecast Rain (mm):", df['forecast_value'].max())
else:
    print("ERROR: forecast_value is not numeric.")
    print("Actual dtype:", df['forecast_value'].dtype)

if pd.api.types.is_numeric_dtype(df['observed_value']):
    print("Negative Observed Rain (Errors):", (df['observed_value'] < 0).sum())
    print("Max Observed Rain (mm):", df['observed_value'].max())
else:
    print("ERROR: observed_value is not numeric.")
    print("Actual dtype:", df['observed_value'].dtype)

print("\n--- Date Range & Completeness ---")

print("Min Date:", df['date'].min())
print("Max Date:", df['date'].max())

print("Unique Dates:", df['date'].nunique(), "/ 122 expected")

