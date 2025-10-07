import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm
from tslearn.clustering import TimeSeriesKMeans
from tslearn.metrics import cdist_dtw
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

# ===========================
# CONFIG
# ===========================
LOOP_MODE = True

DATA_FOLDER = "norms"             # normalized data for clustering
# RAW_TIMESERIES_DIR = "annualized" # folder with raw annualized timeseries
OUTPUT_FOLDER = "output"
MIN_CLUSTERS = 2
MAX_CLUSTERS = 12
RANDOM_STATE = 42

Hex_Codes = {
    'green': '#117733', 'orange': '#D55E00', 'teal': '#44AA99', 'light blue': '#88CCEE',
    'purple': '#AA4499', 'magenta': '#882255', 'coral': '#CC6677', 'booger': '#999933',
    'yellow': '#DDCC77', 'indigo': '#332288', 'blue': '#0072B2', 'grey': '#636363',
}


# ===========================
# CLUSTER AGGREGATION HELPERS
# ===========================
def agg_timeseries(timeseries_csv, mapping, cluster_dfs):
    """Aggregate one timeseries into its correct cluster DataFrame."""
    gage_id = os.path.splitext(os.path.basename(timeseries_csv))[0]
    row = mapping.loc[mapping["site_name"] == gage_id]
    if row.empty:
        return cluster_dfs

    cluster_num = int(row["cluster"].values[0])
    ts = pd.read_csv(timeseries_csv)
    first_col = ts.columns[0].lower()
    ts = ts.set_index(first_col)
    ts_values = ts.iloc[:, 0]
    ts_values.name = gage_id
    ts_values.index = ts_values.index.astype(int)
    ts_values.index.name = first_col

    if cluster_num in cluster_dfs:
        cluster_dfs[cluster_num][gage_id] = ts_values
    else:
        cluster_dfs[cluster_num] = ts_values.to_frame()
    return cluster_dfs


def mean_clusters(cluster_dfs):
    """Compute the mean timeseries for each cluster."""
    out = {}
    for cluster_num, df in cluster_dfs.items():
        df = df.apply(pd.to_numeric, errors="coerce")
        df["cluster_mean"] = df.mean(axis=1)
        out[cluster_num] = df
    return out


def plot_cluster_means(cluster_dfs, title, outfile):
    """Plot mean hydrographs for each cluster."""
    plt.figure(figsize=(14, 7))
    colors = list(Hex_Codes.values())
    cmap = matplotlib.colormaps['Dark2']


    for i, (cluster_num, df) in enumerate(sorted(cluster_dfs.items())):
        df = df.apply(pd.to_numeric, errors="coerce")
        index_name = df.index.name.lower() if df.index.name else "doy"

        if index_name == "dowy":
            start_date = pd.Timestamp("1999-10-01")
        else:
            start_date = pd.Timestamp("2000-01-01")

        dt_index = pd.to_datetime(start_date + pd.to_timedelta(df.index - 1, unit="D"))
        df.index = dt_index

        color = colors[i % len(colors)]  # use with custom hex codes
        # color = colors[i % len(colors)] if i < len(colors) else cmap(i)  # use with cmap
        num_sites = df.shape[1] - 1

        plt.plot(
            df.index, df["cluster_mean"],
            label=f"Cluster {cluster_num} ({num_sites})",
            color=color, linewidth=2
        )

    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b'))
    plt.gca().xaxis.set_major_locator(plt.matplotlib.dates.MonthLocator())
    plt.xlabel("Month")
    plt.ylabel("Discharge (cluster mean)")
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(outfile, dpi=300)
    plt.close()
    print(f"Saved {outfile}")


# ===========================
# MAIN CLUSTERING FUNCTION
# ===========================
def time_warp(input_folder, output_folder):
    """
    Perform DTW-based time series clustering, compute validation metrics,
    and generate aggregated cluster mean plots for both normalized and raw data.
    """
    print(f"\n=== Processing {input_folder} ===")

    time_series_list = []
    file_names = []

    for fname in os.listdir(input_folder):
        if fname.endswith(".csv"):
            df = pd.read_csv(os.path.join(input_folder, fname))
            ts_values = df.values.flatten()
            time_series_list.append(ts_values)
            file_names.append(fname)

    if not time_series_list:
        print(f"No CSV files found in {input_folder}")
        return

    X = np.array(time_series_list)[:, :, np.newaxis]
    X_flat = X.reshape(X.shape[0], -1)

    sil_scores, dbi_scores, ch_scores = [], [], []

    os.makedirs(output_folder, exist_ok=True)

    for k in range(MIN_CLUSTERS, MAX_CLUSTERS + 1):
        print(f"\nClustering with k={k}...")
        model = TimeSeriesKMeans(
            n_clusters=k, metric="dtw", max_iter=10, n_init=2, random_state=RANDOM_STATE
        )
        labels = model.fit_predict(X)

        dtw_dist = cdist_dtw(X)
        sil = silhouette_score(dtw_dist, labels, metric="precomputed")
        dbi = davies_bouldin_score(X_flat, labels)
        ch = calinski_harabasz_score(X_flat, labels)

        sil_scores.append(sil)
        dbi_scores.append(dbi)
        ch_scores.append(ch)

        site_names = [file.replace(".csv", "") for file in file_names]
        mapping_df = pd.DataFrame({"site_name": site_names, "cluster": labels})
        cluster_csv = os.path.join(output_folder, f"dtw_clusters_k{k}.csv")
        mapping_df.to_csv(cluster_csv, index=False)
        print(f"Saved cluster assignments to {cluster_csv}")

        # === Aggregated cluster plots ===
        for data_type, source_dir in [("Normalized", DATA_FOLDER)]:  # [("Normalized", DATA_FOLDER), ("Raw", RAW_TIMESERIES_DIR)]:
            cluster_dfs = {}
            for fname in os.listdir(source_dir):
                if fname.endswith(".csv"):
                    cluster_dfs = agg_timeseries(os.path.join(source_dir, fname), mapping_df, cluster_dfs)
            cluster_dfs = mean_clusters(cluster_dfs)

            out_plot = os.path.join(output_folder, f"{data_type.lower()}_cluster_means_k{k}.png")
            plot_cluster_means(
                cluster_dfs,
                title=f"{data_type} Cluster Mean Hydrographs (k={k})",
                outfile=out_plot,
            )

    # === Summary metric plots ===
    plt.figure(figsize=(15, 5))
    ks = range(MIN_CLUSTERS, MAX_CLUSTERS + 1)

    plt.subplot(1, 3, 1)
    plt.plot(ks, sil_scores, "ro-")
    plt.title("Silhouette Score (↑ better)")
    plt.xlabel("k"); plt.ylabel("Score")

    plt.subplot(1, 3, 2)
    plt.plot(ks, dbi_scores, "go-")
    plt.title("Davies–Bouldin Index (↓ better)")
    plt.xlabel("k"); plt.ylabel("Index")

    plt.subplot(1, 3, 3)
    plt.plot(ks, ch_scores, "bo-")
    plt.title("Calinski–Harabasz Index (↑ better)")
    plt.xlabel("k"); plt.ylabel("Score")

    plt.tight_layout()
    metrics_plot = os.path.join(output_folder, "cluster_metrics.png")
    plt.savefig(metrics_plot, dpi=300)
    plt.close()
    print(f"Saved metric plots to {metrics_plot}")


# ===========================
# MAIN SCRIPT LOGIC
# ===========================
if LOOP_MODE:
    for folder_name in os.listdir(DATA_FOLDER):
        subfolder_path = os.path.join(DATA_FOLDER, folder_name)
        if os.path.isdir(subfolder_path):
            out_subfolder = os.path.join(OUTPUT_FOLDER, folder_name)
            time_warp(subfolder_path, out_subfolder)
else:
    time_warp(DATA_FOLDER, OUTPUT_FOLDER)
