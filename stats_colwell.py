import numpy as np
import pandas as pd

import numpy as np
import pandas as pd

def compute_colwell_stats(df: pd.DataFrame, datetime_col="datetime", flow_col="q",
                          n_time_bins=365, n_flow_bins=11) -> dict:
    """
    Compute Colwell's Constancy (TA1), Predictability (TA2), and Seasonal Predictability of Flooding (TA3)
    from daily flows. Automatically computes 1.67-year flood threshold for TA3.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with datetime and flow columns.
    datetime_col : str
        Column name for datetime values.
    flow_col : str
        Column name for flow values.
    n_time_bins : int
        Number of time bins (default 365 days, leap days removed).
    n_flow_bins : int
        Number of flow bins for Colwell matrix (default 11, log10 scaling).

    Returns
    -------
    dict
        {
            "colwell_constancy": float,
            "colwell_contingency": float,
            "colwell_predictability": float
        }
    """
    df = df.copy()
    df[datetime_col] = pd.to_datetime(df[datetime_col])

    # --- Remove Feb 29th for consistent day-of-year ---
    df = df[~((df[datetime_col].dt.month == 2) & (df[datetime_col].dt.day == 29))]
    df["day"] = df.groupby(df[datetime_col].dt.year).cumcount() + 1

    # --- Compute flow bins (log-scaled like EflowStats) ---
    mean_flow = df[flow_col].mean()
    log_mean_flow = np.log10(mean_flow)
    df["log_flow"] = np.log10(df[flow_col])
    break_pts = np.array([0.1] + list(np.arange(0.25, 2.26, 0.25))) * log_mean_flow
    df["flow_bin"] = np.searchsorted(np.sort(break_pts), df["log_flow"], side="right")

    # --- Colwell matrix ---
    colwell_matrix = pd.crosstab(df["day"], df["flow_bin"]).to_numpy()
    Z = colwell_matrix.sum()
    if Z == 0:
        return {
            "colwell_constancy": np.nan,
            "colwell_contingency": np.nan,
            "colwell_predictability": np.nan,
        }

    # --- Row and column sums ---
    XJ = colwell_matrix.sum(axis=1)
    YI = colwell_matrix.sum(axis=0)

    # --- Entropies ---
    def entropy(vals):
        vals = vals[vals > 0]
        probs = vals / vals.sum()
        return -np.sum(probs * np.log10(probs))

    HX = entropy(XJ)
    HY = entropy(YI)
    HXY = entropy(colwell_matrix.flatten())
    HxY = HXY - HX

    # --- Colwell metrics ---
    colwell_constancy = 1 - (HY / np.log10(n_flow_bins))
    colwell_predictability = 100 * (1 - HxY / np.log10(n_flow_bins))
    colwell_contingency = colwell_predictability - colwell_constancy

    # --- TA3: seasonal predictability of flooding ---
    # Compute 1.67-year flood threshold from annual maxima
    annual_max = df.groupby(df[datetime_col].dt.year)[flow_col].max()
    if len(annual_max) > 0:
        flood_threshold = np.percentile(annual_max, 100 * (1 - 1/1.67))
    else:
        flood_threshold = np.nan

    df["flood_day"] = df[flow_col] > flood_threshold
    df["month"] = df[datetime_col].dt.month

    # 2-month bins like EflowStats: Oct-Nov, Dec-Jan, Feb-Mar, ...
    bins = [(10, 11), (12, 1), (2, 3), (4, 5), (6, 7), (8, 9)]
    flood_counts = []
    for b in bins:
        if b[0] > b[1]:
            mask = df["month"].isin([b[0], b[1]])
        else:
            mask = df["month"].isin(b)
        flood_counts.append(df.loc[mask, "flood_day"].sum())
    total_flood_days = sum(flood_counts)
    ta3 = max(flood_counts) / total_flood_days if total_flood_days > 0 else np.nan

    return {
        "colwell_constancy": colwell_constancy,
        "colwell_contingency": colwell_contingency,
        "colwell_predictability": colwell_predictability,
        "ta3": ta3
    }