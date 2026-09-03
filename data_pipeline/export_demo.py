import pandas as pd

# The historical bust dates P6 chose for the presentation deck.
# Format matches the 'date' string column in your Parquet file (YYYYMMDD)
DEMO_DATES = ['20230708', '20230815', '20230902'] # Ask P6 if they need different dates

print("Extracting demo dates for offline judging...")
df = pd.read_parquet('data-pipeline/output/aligned_pilot.parquet')

# Filter the 6M row dataset down to just the demo dates
demo_df = df[df['date'].isin(DEMO_DATES)]

output_path = 'data-pipeline/output/demo_data_offline.parquet'
demo_df.to_parquet(output_path, index=False)

print(f"Success! Exported {len(demo_df)} rows for offline demo to {output_path}")