import pandas as pd
import numpy as np


def compute_extreme_stats(df):
    """
    Compute annual extreme flow statistics (1-, 3-, 7-, 30-, 90-day minima and maxima).

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain columns ['datetime', 'q']
        Should represent a single water year (or full dataset for all_years).

    Returns
    -------
    dict
        Keys like min_1day, max_1day, min_3day, max_3day, ...
    """
    out = {}
    q = df["q"].astype(float)

    # 1-day extremes are just daily min/max
    out["min_1day"] = q.min()
    out["max_1day"] = q.max()

    # Multi-day rolling means
    for win in [3, 7, 30, 90]:
        rolling = q.rolling(win, min_periods=win).mean()
        out[f"min_{win}day"] = rolling.min()
        out[f"max_{win}day"] = rolling.max()

    return out
