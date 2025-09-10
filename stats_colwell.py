import numpy as np
import pandas as pd

def compute_colwell_stats(df, datetime_col="datetime", flow_col="q",
                  n_time_bins=12, n_flow_bins=10):
    """
        Compute Colwell's Constancy, Contingency, and Predictability (Colwell 1974).

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with datetime and flow columns.
        datetime_col : str, default "date"
            Column name for datetime values.
        flow_col : str, default "discharge"
            Column name for flow values.
        n_time_bins : int, default 12
            Number of time bins (e.g., 12 for months, 52 for weeks).
        n_flow_bins : int, default 10
            Number of flow bins (quantiles).

        Returns
        -------
        dict
            Dictionary with keys:
            - colwell_constancy
            - colwell_contingency
            - colwell_predictability
        """

    df = df.copy()
    df[datetime_col] = pd.to_datetime(df[datetime_col])

    # --- Assign time bins dynamically ---
    # evenly space the dates into n_time_bins
    df["time_bin"] = pd.cut(df[datetime_col].dt.dayofyear,
                            bins=n_time_bins,
                            labels=False,
                            include_lowest=True)

    # --- Assign flow bins by quantiles ---
    df["flow_bin"] = pd.qcut(df[flow_col],
                             q=n_flow_bins,
                             labels=False,
                             duplicates="drop")

    # --- Build frequency matrix ---
    freq_matrix = pd.crosstab(df["time_bin"], df["flow_bin"]).to_numpy()
    total = freq_matrix.sum()
    if total == 0:
        return {
            "colwell_constancy": np.nan,
            "colwell_contingency": np.nan,
            "colwell_predictability": np.nan,
        }

    # --- Probability matrix ---
    P = freq_matrix / total
    row_sums = P.sum(axis=1, keepdims=True)
    col_sums = P.sum(axis=0, keepdims=True)

    # --- Entropies ---
    H_total = -np.nansum(P * np.log(P + 1e-12))
    H_rows = -np.nansum(row_sums * np.log(row_sums + 1e-12))
    H_cols = -np.nansum(col_sums * np.log(col_sums + 1e-12))

    # --- Colwell metrics ---
    constancy = 1 - (H_cols / np.log(n_flow_bins))
    contingency = (H_total - H_rows - H_cols) / np.log(n_time_bins)
    predictability = constancy + contingency

    return {
        "colwell_constancy": float(constancy),
        "colwell_contingency": float(contingency),
        "colwell_predictability": float(predictability),
    }
