import pandas as pd
from eflowstats import EflowStats  # <- assuming class is saved in eflowstats.py

def main():
    # === CONFIG ===
    infile = r"K:\WRD\WMB_GIS\Saba\Classification_Gauges\06036805.csv"       # input CSV with datetime,q
    outfile_m7 = r"output\06036805_hi7.csv"
    outfile_all = r"output\06036805_hiall.csv"
    start_month = 10  # water year start (October)

    print("\n=== Running EflowStats Test Harness ===")

    stats = EflowStats(infile, start_month=start_month)

    # === Magnificent Seven ===
    print("\n--- Magnificent Seven ---")
    magn7 = stats.magnificent_seven()
    stats.save_stats(magn7, outfile_m7)
    print(magn7.head())  # preview

    # === All Stats (future expansion) ===
    if hasattr(stats, "all_stats"):
        print("\n--- All Stats ---")
        allstats = stats.all_stats()
        stats.save_stats(allstats, outfile_all)
        print(allstats.head())
    else:
        print("\n(all_stats() not implemented yet, skipping)")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()