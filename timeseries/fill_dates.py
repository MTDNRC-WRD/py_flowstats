"""Module that takes daily timeseries data and fills any missing date gaps, fills columns with np.nan"""

import os

import pandas as pd

LOOP_MODE = False

CSV_PATH = 'timeseries_raw/06169500.csv'
CSV_OUTPUT = 'timeseries_continuous/06169500.csv'

INPUT_FOLDER = 'timeseries_raw'
OUTPUT_FOLDER = 'timeseries_continuous'


def gap_fill_dates(file_path):
    try:
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")

    # Get the minimum and maximum dates from your data
    min_date = df.index.min()
    max_date = df.index.max()

    # Generate a complete daily date range
    full_date_range = pd.date_range(start=min_date, end=max_date, freq='D')

    # This will add missing dates and fill corresponding 'Value' with NaN
    df_filled = df.reindex(full_date_range)

    return df_filled


if __name__ == '__main__':

    if LOOP_MODE:
        all_files = os.listdir(INPUT_FOLDER)
        for file_name in all_files:
            df_fill = gap_fill_dates(os.path.join(INPUT_FOLDER, file_name))
            print(f"\n{file_name}")
            df_fill.to_csv(os.path.join(OUTPUT_FOLDER, file_name))

    else:
        df_fill = gap_fill_dates(CSV_PATH)
        print(f"\n{CSV_PATH}")
        df_fill.to_csv(CSV_OUTPUT)
