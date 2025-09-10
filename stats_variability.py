import pandas as pd
import numpy as np


def compute_variability_stats(series: pd.Series) -> dict:
    """
    Variability statistics for daily streamflow.

    Parameters
    ----------
    series : pd.Series
        Daily streamflow values.

    Returns
    -------
    dict
        {
            "std_daily": float,
            "cv_daily": float,
            "cv_interannual": float
        }
    """
    values = series.values
    mean_daily = np.nanmean(values)
    std_daily = np.nanstd(values, ddof=1)

    # CV of daily values
    cv_daily = std_daily / mean_daily if mean_daily != 0 else np.nan

    # Interannual CV: std of annual means / mean of annual means
    df = series.to_frame("q").copy()
    df["year"] = df.index.year
    annual_means = df.groupby("year")["q"].mean().values
    mean_annual = np.nanmean(annual_means)
    cv_interannual = np.nanstd(annual_means, ddof=1) / mean_annual if mean_annual != 0 else np.nan

    return {
        "std_daily": std_daily,
        "cv_daily": cv_daily,
        "cv_annual": cv_interannual,
    }