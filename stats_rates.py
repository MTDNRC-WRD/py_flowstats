import numpy as np
import pandas as pd


def compute_rise_fall_stats(df):
    """
    Compute daily rise/fall rates and reversals for a flow series.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain columns ['datetime', 'q']
        Should represent a single water year (or full dataset for all_years).

    Returns
    -------
    dict
        - rise_rate
        - fall_rate
        - reversals
    """
    flows = df["q"].astype(float).values

    if len(flows) < 2:
        return {"rise_rate": np.nan, "fall_rate": np.nan, "reversals": np.nan}

    # Daily differences
    diffs = np.diff(flows)

    # Rise = positive diffs
    rises = diffs[diffs > 0]
    falls = diffs[diffs < 0]

    rise_rate = np.mean(rises) if len(rises) else 0
    fall_rate = np.mean(falls) if len(falls) else 0

    # Count reversals = sign changes in diffs
    signs = np.sign(diffs)
    reversals = np.sum(signs[1:] * signs[:-1] < 0)

    return {
        "rise_rate": rise_rate,
        "fall_rate": fall_rate,
        "reversals": reversals,
    }
