import numpy as np


def compute_baseflow_index(df):
    """
    Compute the Baseflow Index (BFI) as per EflowStats (R version):
    BFI = (minimum 7-day rolling average flow) / (mean flow)

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain 'q' (daily mean flow) for a single water year or the full record.

    Returns
    -------
    dict
        - bfi
    """
    q = df["q"].astype(float)
    mean_flow = q.mean()
    # Compute 7-day rolling average, right-aligned to match R behavior
    rolling7 = q.rolling(window=7, min_periods=7).mean()
    min_7day_avg = rolling7.min()
    bfi = min_7day_avg / mean_flow if mean_flow not in (0, np.nan) else np.nan

    return {"bfi": bfi}