import os
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


LOOP_MODE = False
SITE_FILE = '06061500.csv'
DIRECTORY = 'ts_annualized_joel'


def plot(path, file):
    """
    plots daily timeseries data from nwis output .csv files for visualization and QA/QC purposes
    """
    file_path = os.path.join(path, file)
    ts_df = pd.read_csv(file_path)

    # x_data = ts_df.iloc[:, 0].to_numpy()
    # # x_data = [datetime.strptime(x, '%Y-%m-%d') for x in x_data]
    # x_data = [datetime.strptime(x, '%m-%d') for x in x_data]

    # keep only month-day part
    month_day = ts_df.iloc[:, 0].astype(str)
    # parse into datetime objects with dummy year 2000
    x_data = [datetime.strptime("2000-" + md, "%Y-%m-%d") for md in month_day]
    y_data = ts_df.iloc[:, 1].to_numpy()

    fig, ax = plt.subplots(figsize=(14, 7))
    # ax.scatter(x_data, y_data, s=10, alpha=0.7)
    ax.plot(x_data, y_data)

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
    plt.show()


if __name__ == '__main__':

    if LOOP_MODE:
        all_files = os.listdir(DIRECTORY)
        for file_name in all_files:
            plot(DIRECTORY, file_name)
    else:
        plot(DIRECTORY, SITE_FILE)
