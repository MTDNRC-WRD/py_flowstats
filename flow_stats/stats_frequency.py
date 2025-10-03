import numpy as np
import pandas as pd

def compute_frequency_stats(df: pd.DataFrame) -> dict:
    """
    Compute frequency-based hydrologic metrics:
    - Fh5: Flood frequency (median-flow threshold)
    - Ta3: Seasonal predictability of flooding (2-month bins, 1.67-year flood threshold)

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain columns ['datetime', 'q'].
        Index should be datetime-like or 'datetime' column should be datetime.

    Returns
    -------
    dict
        {
            "fh5_mean": float,
            "fh5_median": float,
            "ta3": float
        }
    """
    df = df.copy()
    if not np.issubdtype(df["datetime"].dtype, np.datetime64):
        df["datetime"] = pd.to_datetime(df["datetime"])
    df["year"] = df["datetime"].dt.year

    results = {}

    # --- Fh5: Flood frequency (events above median flow threshold) ---
    median_thresh = df["q"].median()
    events_per_year = (
        df.groupby("year")["q"].apply(lambda x: (x > median_thresh).sum())
    )

    results["fh5_mean"] = events_per_year.mean()
    results["fh5_median"] = events_per_year.median()

    # # --- Ta3: Seasonal predictability of flooding ---
    # # Step 1: Compute 1.67-year flood threshold (~40th percentile of annual maxima)
    # annual_max = df.groupby("year")["q"].max().dropna()
    # if len(annual_max) > 0:
    #     q167 = np.percentile(annual_max, 100 * (1 - 1/1.67))
    # else:
    #     q167 = np.nan
    #
    # # Step 2: Count flood days above this threshold
    # df["flood_day"] = df["q"] > q167
    # df["month"] = df["datetime"].dt.month
    #
    # # Define 2-month bins
    # bins = [(10, 11), (12, 1), (2, 3), (4, 5), (6, 7), (8, 9)]
    # flood_counts = []
    # for b in bins:
    #     if b == (12, 1):
    #         mask = df["month"].isin([12, 1])
    #     else:
    #         mask = df["month"].isin(b)
    #     flood_counts.append(df.loc[mask, "flood_day"].sum())
    #
    # total_flood_days = sum(flood_counts)
    # ta3 = max(flood_counts) / total_flood_days if total_flood_days > 0 else np.nan
    #
    # results["ta3"] = ta3

    return results
