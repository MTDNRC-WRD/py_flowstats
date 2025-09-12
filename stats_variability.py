import pandas as pd
import numpy as np


def compute_variability_stats(df: pd.DataFrame) -> dict:
    """
    Variability statistics for daily streamflow.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain a 'q' column with daily streamflow values.
        Must also contain a 'datetime' column for annual aggregation.

    Returns
    -------
    dict
        {
            "std_daily": float,
            "cv_daily": float,
            "cv_annual": float
        }
    """
    if "q" not in df.columns:
        raise ValueError("DataFrame must contain a 'q' column.")
    if "datetime" not in df.columns:
        raise ValueError("DataFrame must contain a 'datetime' column.")

    # Ensure numeric values only
    values = pd.to_numeric(df["q"], errors="coerce")

    mean_daily = np.nanmean(values)
    std_daily = np.nanstd(values, ddof=1)

    # CV of daily values
    cv_daily = std_daily / mean_daily if mean_daily != 0 else np.nan

    # Interannual CV: std of annual means / mean of annual means
    df_copy = df[["q", "datetime"]].copy()
    df_copy["year"] = df_copy["datetime"].dt.year
    annual_means = df_copy.groupby("year")["q"].mean().values
    mean_annual = np.nanmean(annual_means)
    cv_interannual = np.nanstd(annual_means, ddof=1) / mean_annual if mean_annual != 0 else np.nan

    return {
        "std_daily": std_daily,
        "cv_daily": cv_daily,
        "cv_annual": cv_interannual,
    }
