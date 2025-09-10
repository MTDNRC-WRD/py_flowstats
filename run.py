import pandas as pd
from eflowstats import EflowStats  # assumes eflowstats.py is in the same folder

def main():
    # === CONFIG ===
    infile = r"K:\WRD\WMB_GIS\Saba\Classification_Gauges\06037500.csv"   # input CSV (datetime,q)
    outfile_m7 = r"output\06037500.csv"
    outfile_all = r"output\06037500_allstats.csv"
    start_month = 10  # October = start of water year

    print("\n=== Running EflowStats Test Harness ===")

    # --- Initialize ---
    stats = EflowStats(infile, start_month=start_month)

    # --- Magnificent Seven ---
    print("\n--- Magnificent Seven ---")
    try:
        magn7 = stats.magnificent_seven()
        stats.save_stats(magn7, outfile_m7)
        print(magn7.head())
    except Exception as e:
        print(f"Error running magnificent_seven(): {e}")

    # --- All Stats ---
    print("\n--- All Stats ---")
    try:
        allstats = stats.all_stats()
        stats.save_stats(allstats, outfile_all)
        # show a preview with only first few columns for readability
        print(allstats.iloc[:, :8].head())
        print(f"\nTotal metrics computed: {allstats.shape[1] - 1}")  # exclude water_year
    except Exception as e:
        print(f"Error running all_stats(): {e}")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()