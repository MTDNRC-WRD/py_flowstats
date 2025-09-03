import numpy as np
import pandas as pd


def compute_timing_stats(df):
    """
    Compute seasonality/timing metrics for a flow series.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain columns ['datetime', 'q']
        Should represent a single water year (or full dataset for all_years).

    Returns
    -------
    dict
        - doy_max: Day of year of annual maximum flow
        - doy_min: Day of year of annual minimum flow
        - center_of_timing: Flow-weighted center of timing (day of year)
    """
    df = df.copy()
    df["doy"] = df["datetime"].dt.dayofyear

    # Max flow DOY
    idx_max = df["q"].idxmax()
    doy_max = int(df.loc[idx_max, "doy"]) if not pd.isna(idx_max) else None

    # Min flow DOY
    idx_min = df["q"].idxmin()
    doy_min = int(df.loc[idx_min, "doy"]) if not pd.isna(idx_min) else None

    # Center of Timing (flow-weighted mean DOY)
    if df["q"].sum() > 0:
        center_of_timing = np.average(df["doy"], weights=df["q"])
    else:
        center_of_timing = None

    return {
        "doy_max": doy_max,
        "doy_min": doy_min,
        "center_of_timing": center_of_timing,
    }
