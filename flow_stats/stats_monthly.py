import pandas as pd
import numpy as np


def compute_monthly_stats(df):
    """
    Compute mean/median monthly flow for a given year's dataframe.
    Expects columns: ['datetime', 'q']

    Returns
    -------
    dict
        Keys like 'mean_month_01', 'median_month_01', ..., 'mean_month_12', 'median_month_12'
    """
    df = df.copy()
    df["month"] = df["datetime"].dt.month
    monthly = df.groupby("month")["q"].agg(["mean", "median"])
    out = {}
    for m in range(1, 13):
        if m in monthly.index:
            out[f"mean_month_{m:02d}"] = monthly.loc[m, "mean"]
            out[f"median_month_{m:02d}"] = monthly.loc[m, "median"]
        else:
            out[f"mean_month_{m:02d}"] = np.nan
            out[f"median_month_{m:02d}"] = np.nan
    return out
