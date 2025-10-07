import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm


# === CONFIG ===
DIRECTORY = 'ts_min_max_log_mean'       # folder with input timeseries CSVs
CLUSTER_CSV = 'timewarp_results/ann_flow_index_log_mean_7day_k5.csv'   # site-to-cluster mapping

Hex_Codes = {
    'green': '#117733',
    'orange': '#D55E00',
    'teal': '#44AA99',
    'light blue': '#88CCEE',
    'purple': '#AA4499',
    'magenta': '#882255',
    'coral': '#CC6677',
    'booger': '#999933',
    'yellow': '#DDCC77',
    'indigo': '#332288',
    'blue': '#0072B2',
    'grey': '#DDDDDD',
}


def agg_timeseries(timeseries_csv, mapping, cluster_dfs):
    """
    Aggregate a timeseries into the correct in-memory cluster DataFrame.
    """
    gage_id = os.path.splitext(os.path.basename(timeseries_csv))[0]

    # Lookup cluster assignment
    row = mapping.loc[mapping["site_name"] == gage_id]
    if row.empty:
        print(f"⚠️ Gage ID {gage_id} not found in mapping.")
        return cluster_dfs

    cluster_num = int(row["cluster"].values[0])

    # Load timeseries
    ts = pd.read_csv(timeseries_csv)

    first_col = ts.columns[0].lower()
    if first_col not in ["doy", "dowy"]:
        raise ValueError(f"Unexpected first column {first_col} in {timeseries_csv}")

    # Store both the values and the type of index
    ts = ts.set_index(first_col)
    ts_values = ts.iloc[:, 0]
    ts_values.name = gage_id
    ts_values.index = ts_values.index.astype(int)
    ts_values.index.name = first_col  # keep track of doy vs dowy

    # Add to cluster dict
    if cluster_num in cluster_dfs:
        cluster_dfs[cluster_num][gage_id] = ts_values
    else:
        cluster_dfs[cluster_num] = ts_values.to_frame()

    return cluster_dfs


def mean_clusters(cluster_dfs):
    out = {}
    for cluster_num, df in cluster_dfs.items():
        df = df.apply(pd.to_numeric, errors="coerce")
        df["cluster_mean"] = df.mean(axis=1)
        out[cluster_num] = df
        print(f"Cluster {cluster_num}: {df.shape[1]-1} sites")
    return out


def plot_cluster_means(cluster_dfs, plot_dates=True, monthly=False):
    import matplotlib.dates as mdates

    plt.figure(figsize=(14, 7))
    colors = list(Hex_Codes.values())
    cmap = matplotlib.colormaps['Dark2']

    for i, (cluster_num, df) in enumerate(sorted(cluster_dfs.items())):
        df = df.apply(pd.to_numeric, errors="coerce")

        # Detect if index is doy or dowy
        index_name = df.index.name.lower() if df.index.name else "doy"

        if plot_dates:
            if index_name == "dowy":
                # water year starts Oct 1 of prior year
                start_date = pd.Timestamp("1999-10-01")
            else:
                # normal calendar year
                start_date = pd.Timestamp("2000-01-01")

            dt_index = pd.to_datetime(start_date + pd.to_timedelta(df.index - 1, unit="D"))
            df.index = dt_index

        # Optionally aggregate monthly
        if monthly:
            df = df.groupby(df.index.month).mean()
            x_vals = pd.to_datetime("2000-" + df.index.astype(str) + "-15")
        else:
            x_vals = df.index

        color = colors[i % len(colors)] if i < len(colors) else cmap(i)
        num_sites = df.shape[1] - 1

        plt.plot(
            x_vals,
            df["cluster_mean"],
            label=f"Cluster {cluster_num}: {num_sites}",
            color=color,
            linewidth=2
        )

    if plot_dates:
        if monthly:
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b'))
            plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
            plt.xlabel("Month")
        else:
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b'))
            plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
            plt.xlabel("Month")
    else:
        plt.xlabel("Day Index")

    plt.ylabel("Discharge (cluster mean)")
    plt.title("Cluster Mean Hydrographs")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    mapping = pd.read_csv(CLUSTER_CSV)
    cluster_dfs = {}

    for file_name in os.listdir(DIRECTORY):
        cluster_dfs = agg_timeseries(os.path.join(DIRECTORY, file_name), mapping, cluster_dfs)

    cluster_dfs = mean_clusters(cluster_dfs)

    plot_cluster_means(cluster_dfs, monthly=False)
