import os
import pandas as pd
from eflowstats import EflowStats

INPUT_DIR = "input"
OUTPUT_DIR = "output"
COMPILED_FILENAME = "compiled_all_sites.csv"

# Create output folder if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

compiled_rows = []

for filename in os.listdir(INPUT_DIR):
    if filename.lower().endswith(".csv"):
        filepath = os.path.join(INPUT_DIR, filename)
        site_name = os.path.splitext(filename)[0]

        # Initialize EflowStats object for this CSV
        ef_stats = EflowStats(filepath)

        # Compute HIAP stats using the cleaned internal dataframe
        stats_df = ef_stats.HIAP_stats()

        # Save full stats for this site
        output_file = os.path.join(OUTPUT_DIR, f"{site_name}_HIAP_stats.csv")
        stats_df.to_csv(output_file, index=False)

        # Append the all_years row for compilation
        all_years_row = stats_df[stats_df["water_year"] == "all_years"].copy()
        all_years_row.insert(0, "site_name", site_name)
        compiled_rows.append(all_years_row)

# Concatenate all compiled rows into a single DataFrame
if compiled_rows:
    compiled_df = pd.concat(compiled_rows, ignore_index=True)
    compiled_file_path = os.path.join(OUTPUT_DIR, COMPILED_FILENAME)
    compiled_df.to_csv(compiled_file_path, index=False)

print(f"All HIAP stats processed. Individual CSVs saved in '{OUTPUT_DIR}' and compiled CSV saved as '{COMPILED_FILENAME}'.")