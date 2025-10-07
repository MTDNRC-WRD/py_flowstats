import os
import numpy as np
import pandas as pd

LOOP_MODE = True
CSV_PATH = 'timeseries/06169500.csv'
CSV_OUTPUT = 'ts_normalized/06169500.csv'

INPUT_FOLDER = 'timeseries'
OUTPUT_FOLDER = 'ts_ann_flow_index_log_mean_7day'


def normalize(file_path, method, log=True, moving_average=False, annualize=False,
              annualize_method='median', water_year=True):
    """
    Normalize and optionally smooth or annualize a daily streamflow time series.

    Parameters
    ----------
    file_path : str
        Path to a CSV with at least two columns: datetime index and 'q' (flow).
    method : str
        Normalization method:
        - 'min_max'          : Rescale values to [0, 1] using global min/max.
        - 'mean_variance'    : Standardize by subtracting mean and dividing by std.
        - 'flow_index'       : Divide by the mean of the entire timeseries (long-term mean).
        - 'annual_flow_index': Divide each year by its annual mean (focuses on shape).
    log : bool, default=True
        Apply log1p transform to flows before normalization (except for flow index methods,
        where log is applied afterward).
    moving_average : bool, default=False
        If True, apply a 7-day centered moving average to the final normalized series.
        Smoothing occurs after normalization and optional annualization.
    annualize : bool, default=False
        If True, aggregate values by day-of-year (or day-of-water-year).
    annualize_method : {'median', 'mean'}, default='median'
        Aggregation method when annualizing.
    water_year : bool, default=True
        If True, compute day-of-water-year (Oct–Sep). If False, use calendar year (Jan–Dec).

    Returns
    -------
    pd.DataFrame or pd.Series
        Normalized (and optionally smoothed and/or annualized) flow time series.
        If annualized, index is DOY/DOWY and values are aggregated.
    """
    try:
        ts_df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None

    # Ensure datetime index is clean
    ts_df.index = pd.to_datetime(ts_df.index, errors="coerce", utc=True)
    ts_df.index = ts_df.index.tz_localize(None)

    # --- Log transform (pre-normalization, except for flow index methods) ---
    if log:
        if method not in ('flow_index', 'annual_flow_index'):
            ts_df['q'] = np.log1p(ts_df['q'])

    # --- Normalization methods ---
    if method == 'min_max':
        min_val = ts_df['q'].min()
        max_val = ts_df['q'].max()
        ts_df['q'] = (ts_df['q'] - min_val) / (max_val - min_val)

    elif method == 'mean_variance':
        mean_val = ts_df['q'].mean()
        std_val = ts_df['q'].std(ddof=0)
        ts_df['q'] = (ts_df['q'] - mean_val) / std_val

    elif method == 'flow_index':
        mean_val = ts_df['q'].mean()
        ts_df['q'] = ts_df['q'] / mean_val
        if log:
            ts_df['q'] = np.log1p(ts_df['q'])

    elif method == 'annual_flow_index':
        # Compute annual mean (calendar or water year)
        if water_year:
            year_col = ts_df.index.year + (ts_df.index.month >= 10)
        else:
            year_col = ts_df.index.year
        ts_df['year'] = year_col
        annual_means = ts_df.groupby('year')['q'].transform('mean')
        ts_df['q'] = ts_df['q'] / annual_means
        ts_df.drop(columns=['year'], inplace=True)
        if log:
            ts_df['q'] = np.log1p(ts_df['q'])
    else:
        raise ValueError(f"Unknown normalization method: {method}")

    # --- Annualize if requested ---
    if annualize:
        # Drop leap day
        ts_df = ts_df[~((ts_df.index.month == 2) & (ts_df.index.day == 29))]

        if water_year:
            ts_df["water_year"] = ts_df.index.year + (ts_df.index.month >= 10)
            start = pd.to_datetime((ts_df["water_year"] - 1).astype(str) + "-10-01")
            ts_df["dowy"] = (ts_df.index - start).dt.days + 1
            if annualize_method == 'median':
                ts_df = ts_df.groupby("dowy")["q"].median()
            else:
                ts_df = ts_df.groupby("dowy")["q"].mean()
        else:
            ts_df["doy"] = ts_df.index.dayofyear
            if annualize_method == 'median':
                ts_df = ts_df.groupby("doy")["q"].median()
            else:
                ts_df = ts_df.groupby("doy")["q"].mean()

    # --- Apply 7-day moving average if requested ---
    if moving_average:
        if isinstance(ts_df, pd.Series):
            ts_df = ts_df.rolling(window=7, center=True, min_periods=1).mean()
        else:
            ts_df['q'] = ts_df['q'].rolling(window=7, center=True, min_periods=1).mean()

    return ts_df


# --- Main loop ---
if __name__ == '__main__':
    if LOOP_MODE:
        # Create output folder if it doesn't exist
        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)
            print(f"Created output folder: {OUTPUT_FOLDER}")

        all_files = os.listdir(INPUT_FOLDER)
        for file_name in all_files:
            df_fill = normalize(
                os.path.join(INPUT_FOLDER, file_name),
                method='annual_flow_index',
                log=True,
                annualize=True,
                annualize_method='mean',
                water_year=True,
                moving_average=True
            )
            print(f"\n{file_name}")
            if df_fill is not None:
                df_fill.to_csv(os.path.join(OUTPUT_FOLDER, file_name))
    else:
        df_fill = normalize(CSV_PATH, method="annual_flow_index",
                            annualize=True, water_year=True, log=True, moving_average=True)
        print(f"\n{CSV_PATH}")
        if df_fill is not None:
            df_fill.to_csv(CSV_OUTPUT)
