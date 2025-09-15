import numpy as np
import pandas as pd


def compute_timing_stats(df, all_years=False):
    """
    Compute seasonality/timing metrics for a flow series.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain columns ['datetime', 'q'].
        Should represent a single water year (or full dataset for all_years).
    all_years : bool
        If True, compute CV of Julian min/max across years.

    Returns
    -------
    dict
        - julian_max: Day of year of annual maximum flow
        - julian_min: Day of year of annual minimum flow
        - center_of_timing: Flow-weighted center of timing (day of year)
        - cv_julian_max: Coefficient of variation of Julian max (only if all_years=True)
        - cv_julian_min: Coefficient of variation of Julian min (only if all_years=True)
    """
    df = df.copy()
    df["doy"] = df["datetime"].dt.dayofyear

    # Max flow DOY
    idx_max = df["q"].idxmax()
    doy_max = int(df.loc[idx_max, "doy"]) if not pd.isna(idx_max) else np.nan

    # Min flow DOY
    idx_min = df["q"].idxmin()
    doy_min = int(df.loc[idx_min, "doy"]) if not pd.isna(idx_min) else np.nan

    # Center of Timing (flow-weighted mean DOY)
    center_of_timing = np.average(df["doy"], weights=df["q"]) if df["q"].sum() > 0 else np.nan

    result = {
        "julian_max": doy_max,
        "julian_min": doy_min,
        "center_of_timing": center_of_timing,
    }

    if all_years:
        # Group by water year to get DOY of min/max per year
        julian_maxs = df.groupby("water_year").apply(lambda x: x.loc[x["q"].idxmax(), "doy"])
        julian_mins = df.groupby("water_year").apply(lambda x: x.loc[x["q"].idxmin(), "doy"])

        # CV = std / mean
        result["cv_julian_max"] = julian_maxs.std(ddof=1) / julian_maxs.mean() if julian_maxs.mean() != 0 else np.nan
        result["cv_julian_min"] = julian_mins.std(ddof=1) / julian_mins.mean() if julian_mins.mean() != 0 else np.nan

    return result


# def compute_phase_amplitude(df: pd.DataFrame) -> dict:
#     """
#     Note: this has been depreciated, see compute_mag7_stats instead
#
#     Compute phase and amplitude of seasonal streamflow using harmonic regression.
#
#     Parameters
#     ----------
#     df : pd.DataFrame
#         Must have a datetime index and a 'q' column of daily streamflow.
#
#     Returns
#     -------
#     dict
#         {
#             "phase": float,       # peak timing (day of year, 1–366)
#             "amplitude": float    # strength of seasonal cycle
#         }
#     """
#
#     # Drop NaNs in discharge
#     series = df["q"].dropna()
#     if series.empty:
#         return {"phase": np.nan, "amplitude": np.nan}
#
#     # Day of year (1–366), convert to radians
#     doy = series.index.dayofyear.values
#     radians = 2 * np.pi * doy / 365.25
#
#     # Response variable
#     y = series.values
#
#     # Harmonic regression design matrix
#     X = np.column_stack([
#         np.cos(radians),
#         np.sin(radians)
#     ])
#
#     # Fit regression (least squares)
#     beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
#     beta_cos, beta_sin = beta
#
#     # Amplitude (magnitude of seasonal signal)
#     amplitude = np.sqrt(beta_cos**2 + beta_sin**2)
#
#     # Phase (peak timing) in radians -> day of year
#     phase_rad = np.arctan2(beta_sin, beta_cos)
#     if phase_rad < 0:
#         phase_rad += 2 * np.pi
#     phase_doy = phase_rad * 365.25 / (2 * np.pi)
#
#     return {
#         "phase": float(phase_doy),
#         "amplitude": float(amplitude),
#     }
