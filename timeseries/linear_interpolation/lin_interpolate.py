import os

import matplotlib.pyplot as plt
import pandas as pd


LOOP_MODE = False

INPUT_FOLDER = 'ts_raw'
OUTPUT_FOLDER = 'ts_lin'

CSV_PATH = os.path.join(INPUT_FOLDER, '41S_08900.csv')
CSV_OUTPUT = os.path.join(OUTPUT_FOLDER, '41S_08900.csv')


import os
import pandas as pd
import matplotlib.pyplot as plt


def linear_interpolate(filepath, sp_gap, ot_gap, plot=True):
    df = pd.read_csv(filepath, index_col=0, parse_dates=True)

    # Ensure daily frequency
    df = df.asfreq("D")

    # Track original NaN mask
    is_nan = df['q'].isna()

    if not is_nan.any():
        print(f"No gaps found in {os.path.basename(filepath)}")
        if plot:
            plt.figure(figsize=(12, 5))
            plt.plot(df.index, df['q'], color='blue', label='Original (no gaps)')
            plt.title(os.path.basename(filepath))
            plt.xlabel("Date")
            plt.ylabel("q")
            plt.legend()
            plt.tight_layout()
            plt.show()
        return df

    # Find consecutive NaN blocks
    gap_id = (is_nan != is_nan.shift()).cumsum()
    gaps = df[is_nan].groupby(gap_id).apply(lambda g: g.index)

    # Work on a copy
    df_out = df.copy()

    # Collect interpolated indices
    interpolated_idx = []

    for _, gap_dates in gaps.items():
        gap_len = len(gap_dates)
        start_date = gap_dates[0]
        end_date = gap_dates[-1]

        # Define season
        in_spring = (start_date.month >= 3) and (start_date.month <= 7)
        rule_gap = sp_gap if in_spring else ot_gap

        if gap_len <= rule_gap:
            # Interpolate just this gap
            df_out['q'] = df_out['q'].interpolate(method='linear', limit_area='inside')
            interpolated_idx.extend(gap_dates)

            print(f"Interpolated gap {start_date.date()} → {end_date.date()} "
                  f"({gap_len} days, {'spring' if in_spring else 'other'})")
        else:
            print(f"Skipped gap {start_date.date()} → {end_date.date()} "
                  f"({gap_len} days, too long for {'spring' if in_spring else 'other'})")

    # Plot
    if plot:
        plt.figure(figsize=(12, 5))
        plt.plot(df.index, df['q'], color='blue', label='Original')
        if interpolated_idx:
            plt.scatter(df_out.loc[interpolated_idx].index,
                        df_out.loc[interpolated_idx, 'q'],
                        color='red', label='Interpolated', zorder=5)
        plt.title(os.path.basename(filepath))
        plt.xlabel("Date")
        plt.ylabel("q")
        plt.legend()
        plt.tight_layout()
        plt.show()

    return df_out


if __name__ == '__main__':

    gap_len_sp = 7
    gap_len_ot = 22

    if LOOP_MODE:
        all_files = os.listdir(INPUT_FOLDER)
        for file_name in all_files:
            print(f"\n{file_name}")
            filepath = os.path.join(INPUT_FOLDER, file_name)
            df_intr = linear_interpolate(os.path.join(filepath), gap_len_sp, gap_len_ot, plot=False)
            df_intr.to_csv(os.path.join(OUTPUT_FOLDER, file_name))

    else:
        print(f"\n{CSV_PATH}")
        df_intr = linear_interpolate(CSV_PATH, gap_len_sp, gap_len_ot)
        df_intr.to_csv(CSV_OUTPUT)