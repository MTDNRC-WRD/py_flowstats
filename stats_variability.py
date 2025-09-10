import pandas as pd
import numpy as np


def compute_variability_stats(df):
    """
    Compute variability metrics:
    - Coefficient of inter-annual variation (std/mean of annual mean flows)
    - Standard deviation of daily streamflow (period-of-record)

    Expects columns: ['datetime', 'q']
    """
    df = df.copy()
    df["year"] = df["datetime"].dt.year

    # Annual mean flows
    annual_means = df.groupby("year")["q"].mean()

    # CV of inter-annual variation
    if len(annual_means) > 1:
        cv_interannual = annual_means.std() / annual_means.mean()
    else:
        cv_interannual = np.nan

    # Std dev of daily flows (all years pooled)
    std_daily = df["q"].std()

    return {
        "cv_interannual": cv_interannual,
        "std_daily": std_daily,
    }