import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from tslearn.clustering import TimeSeriesKMeans
from tslearn.metrics import cdist_dtw
from sklearn.metrics import silhouette_score, davies_bouldin_score

# ===========================
# CONFIG
# ===========================
LOOP_MODE = True

DATA_FOLDER = "norms"
OUTPUT_FOLDER = "output"
MIN_CLUSTERS = 2
MAX_CLUSTERS = 12
RANDOM_STATE = 42


# ===========================
# FUNCTION TO PROCESS A FOLDER
# ===========================
def time_warp (input_folder, output_folder):
    print(f"\n=== Processing {input_folder} ===")

    # Collect all CSVs
    time_series_list = []
    file_names = []

    for fname in os.listdir(input_folder):
        if fname.endswith(".csv"):
            df = pd.read_csv(os.path.join(input_folder, fname))
            ts_values = df.values.flatten()  # assumes single column per CSV
            time_series_list.append(ts_values)
            file_names.append(fname)

    if not time_series_list:
        print(f"No CSV files found in {input_folder}")
        return

    # Convert to tslearn format: (n_ts, sz, 1)
    X = np.array(time_series_list)[:, :, np.newaxis]
    X_flat = X.reshape(X.shape[0], -1)

    sil_scores = []
    dbi_scores = []

    # Make sure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    for k in range(MIN_CLUSTERS, MAX_CLUSTERS + 1):
        print(f"\nClustering with k={k}...")
        model = TimeSeriesKMeans(
            n_clusters=k,
            metric="dtw",
            max_iter=10,
            n_init=2,
            random_state=RANDOM_STATE,
        )
        labels = model.fit_predict(X)

        # Compute pairwise DTW distance matrix for silhouette
        dtw_dist = cdist_dtw(X)
        sil = silhouette_score(dtw_dist, labels, metric="precomputed")
        sil_scores.append(sil)

        # Davies-Bouldin index on flattened series
        dbi = davies_bouldin_score(X_flat, labels)
        dbi_scores.append(dbi)

        # Save cluster assignments
        site_names = [file.replace(".csv", "") for file in file_names]
        out_df = pd.DataFrame({"site_name": site_names, "cluster": labels})
        out_csv = os.path.join(output_folder, f"dtw_clusters_k{k}.csv")
        out_df.to_csv(out_csv, index=False)
        print(f"Saved cluster assignments to {out_csv}")
        print(f"Silhouette score: {sil:.4f}, DBI: {dbi:.4f}")

    # ===========================
    # PLOT METRICS VS K
    # ===========================
    plt.figure(figsize=(12, 5))

    # Silhouette
    plt.subplot(1, 2, 1)
    plt.plot(range(MIN_CLUSTERS, MAX_CLUSTERS + 1), sil_scores, "ro-")
    plt.xlabel("Number of clusters (k)")
    plt.ylabel("Silhouette Score")
    plt.title("Silhouette Score vs k")

    # Davies-Bouldin
    plt.subplot(1, 2, 2)
    plt.plot(range(MIN_CLUSTERS, MAX_CLUSTERS + 1), dbi_scores, "go-")
    plt.xlabel("Number of clusters (k)")
    plt.ylabel("Davies-Bouldin Index")
    plt.title("Davies-Bouldin Index vs k (lower is better)")

    plt.tight_layout()

    out_plot = os.path.join(output_folder, "cluster_metrics.png")
    plt.savefig(out_plot, dpi=300)
    plt.close()
    print(f"Saved plot to {out_plot}")


# ===========================
# MAIN LOGIC
# ===========================
if LOOP_MODE:
    for folder_name in os.listdir(DATA_FOLDER):
        subfolder_path = os.path.join(DATA_FOLDER, folder_name)
        if os.path.isdir(subfolder_path):
            out_subfolder = os.path.join(OUTPUT_FOLDER, folder_name)
            time_warp(subfolder_path, out_subfolder)
else:
    time_warp(DATA_FOLDER, OUTPUT_FOLDER)