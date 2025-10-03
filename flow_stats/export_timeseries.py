import os
import pandas as pd
from eflowstats import EflowStats


INPUT_DIR = "input"
OUTPUT_DIR = "cleaned_ts"


for filename in os.listdir(INPUT_DIR):
    if filename.lower().endswith(".csv"):
        filepath = os.path.join(INPUT_DIR, filename)
        site_name = os.path.splitext(filename)[0]

        # Initialize EflowStats object for this CSV
        ef_stats = EflowStats(filepath)
        ts_df = ef_stats.export_timeseries()

        output_file = os.path.join(OUTPUT_DIR, f"{site_name}.csv")
        ts_df.to_csv(output_file, index=False)
