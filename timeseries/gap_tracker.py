"""Module that tracks gaps in timeseries data and returns list of all data gaps in terminal

Config settings:
     -LOOP_MODE: True will loop through all timeseries downloads in outputs folder, False will only run a single specified site
     -SITE_FILE: When LOOP_MODE is False, giving the file name in the output directory will call that file only
     -OUTPUT_PATH: filepath to folder containing timeseries data
     -GAP_DAYS: number of days (int) required to trigger the data_gap message
     """

import os
import warnings

import pandas as pd

warnings.simplefilter(action='ignore', category=FutureWarning)

LOOP_MODE = False
SITE_FILE = '06169500.csv'
OUTPUT_PATH = 'timeseries_continuous'
GAP_DAYS = 0


def gap_track(path, file, min_gap_duration_days=GAP_DAYS):
    """
    Identifies missing daily date ranges in a pandas DataFrame that are
    longer than a specified duration, and returns them as a list.

    Args:
        df (pd.DataFrame): The input DataFrame. It should ideally have a DatetimeIndex.
                           If not, the function will attempt to convert the first
                           column to datetime and set it as the index.
        min_gap_duration_days (int): The minimum duration in days for a gap
                                      to be considered significant.

    Returns:
        list: A list of dictionaries, where each dictionary represents a gap
              and has 'start' and 'end' keys (pandas Timestamps) and 'duration_days'.
              Returns an empty list if no gaps are found or if the DataFrame
              is not suitable.
    """
    file_path = os.path.join(path, file)
    df = pd.read_csv(file_path)

    # 1. Ensure the DataFrame has a proper DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        # print("Warning: DataFrame index is not DatetimeIndex. Attempting to convert first column to index.")
        if df.empty:
            print("Error: DataFrame is empty, cannot process for gaps.")
            return []
        try:
            # Create a copy to avoid modifying the original DataFrame directly
            df_processed = df.copy()
            # Attempt to convert the first column to datetime and set as index
            df_processed.iloc[:, 0] = pd.to_datetime(df_processed.iloc[:, 0])
            # pandas yells at me because I don't specify object types, future warning
            df_processed = df_processed.set_index(df_processed.columns[0])
            df = df_processed  # Use the processed DataFrame
        except Exception as e:
            print(
                f"Error: Could not convert a column to DatetimeIndex. "
                f"Please ensure your DataFrame has a datetime index or a suitable date column: {e}")
            return []

    if df.empty:
        print("DataFrame is empty after processing, no gaps to find.")
        return []

    # 2. Create a continuous daily date range covering the entire period
    min_date = df.index.min()
    max_date = df.index.max()
    full_daily_index = pd.date_range(start=min_date, end=max_date, freq='D')

    # 3. Reindex the DataFrame to this full daily range.
    # This will introduce NaN values for any missing days.
    # We only need one column to check for NaNs. If there are no data columns,
    # we infer gaps directly from the missing index entries.
    if df.shape[1] == 0:
        # If DataFrame only has an index, missing dates are those in full_daily_index not in df.index
        missing_dates_in_index = full_daily_index.difference(df.index)
        is_missing_series = pd.Series(True, index=missing_dates_in_index)
        # Combine with False for existing dates to make it a continuous boolean series
        existing_dates_series = pd.Series(False, index=df.index)
        boolean_mask = pd.concat([is_missing_series, existing_dates_series]).sort_index()
        missing_days_indices = boolean_mask[boolean_mask].index  # Get only the dates where it's True (missing)
    else:
        # Reindex and check for NaNs in the first data column
        df_reindexed = df.reindex(full_daily_index)
        # Identify where the first data column is NaN
        is_missing_series = df_reindexed.iloc[:, 0].isna()
        missing_days_indices = is_missing_series[
            is_missing_series].index  # Get only the dates where it's True (missing)

    # 4. Group consecutive missing days and calculate their duration
    gap_list = []
    current_gap_start = None

    # Iterate through the index of the identified missing days
    for i, date in enumerate(missing_days_indices):
        if current_gap_start is None:
            current_gap_start = date

        # Determine the next expected day if the gap were to continue
        next_expected_day = date + pd.Timedelta(days=1)

        # Check if the current gap is ending:
        # - It's the last missing day in the list, OR
        # - The next day in the `missing_days_indices` list is not the `next_expected_day`
        if (i + 1 == len(missing_days_indices)) or (missing_days_indices[i + 1] != next_expected_day):
            current_gap_end = date
            duration_days = (current_gap_end - current_gap_start).days + 1  # +1 to include both start and end day

            # 5. Filter by minimum gap duration
            if duration_days > min_gap_duration_days:
                gap_list.append({
                    'start': current_gap_start.strftime('%Y-%m-%d'),
                    'end': current_gap_end.strftime('%Y-%m-%d'),
                    'duration_days': duration_days
                })
            current_gap_start = None  # Reset for the next potential gap

    return gap_list


if __name__ == '__main__':

    if LOOP_MODE:
        all_files = os.listdir(OUTPUT_PATH)
        for file_name in all_files:
            gaps = gap_track(OUTPUT_PATH, file_name)
            print(f"\n{file_name}")
            if not gaps:
                print("No significant gaps detected")
            for gap in gaps:
                print(gap)

    else:
        gaps = gap_track(OUTPUT_PATH, SITE_FILE)
        print(f"\n{SITE_FILE}")
        if not gaps:
            print("No significant gaps detected")
        for gap in gaps:
            print(gap)
