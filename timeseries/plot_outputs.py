"""
Module that outputs graph of timeseries data.

Config settings:
     -LOOP_MODE: True will loop through all timeseries downloads in outputs folder, False will only run a single specified site
     -SITE_FILE: When LOOP_MODE is False, giving the file name in the output directory will call that file only
     -OUTPUT_PATH: filepath to folder containing timeseries data
"""

import os
from datetime import datetime
import numpy as np

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from fontTools.unicodedata import block

LOOP_MODE = True
SITE_FILE = '40B_06000.csv'
OUTPUT_PATH = 'timeseries_continuous'


def plot(path, file):
    """
    plots daily timeseries data from nwis output .csv files for visualization and QA/QC purposes
    """
    file_path = os.path.join(path, file)
    ts_df = pd.read_csv(file_path)

    x_data = ts_df.iloc[:, 0].to_numpy()
    try:
        x_data = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S+00:00') for x in x_data]
    except ValueError:
        x_data = [datetime.strptime(x, '%Y-%m-%d') for x in x_data]

    y_data = ts_df.iloc[:, 1].to_numpy()

    fig, ax = plt.subplots(figsize=(14, 7))
    # ax.scatter(x_data, y_data, s=10, alpha=0.7)

    # colors = ['red' if val == 0 else 'blue' for val in y_data]

    ax.plot(x_data, y_data, color='blue')


    # Set major ticks every 5 years
    ax.xaxis.set_major_locator(mdates.YearLocator(base=5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_minor_locator(mdates.YearLocator())
    fig.autofmt_xdate()

    ax.set_ylim(bottom=0)
    # plt.yscale('symlog') # cannot use with previous line

    plt.xlabel("Day")
    plt.ylabel("Discharge (cfs)")
    plt.title(f"{file}")
    plt.grid(True)
    plt.show(block=True)


if __name__ == '__main__':


    if LOOP_MODE:
        all_files = os.listdir(OUTPUT_PATH)
        for file_name in all_files:
            plot(OUTPUT_PATH, file_name)

    else:
        plot(OUTPUT_PATH, SITE_FILE)
