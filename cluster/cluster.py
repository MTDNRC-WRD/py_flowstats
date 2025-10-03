import os
os.environ["OMP_NUM_THREADS"] = "1"
import pandas as pd
from sklearn import cluster
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import numpy as np

class Clusterer:
    def __init__(self, method, n_clusters, random_state=42, **kwargs):
        """
        Initialize the clustering module.

        Parameters
        ----------
        method : str
            Clustering method. Currently only 'kmeans' is implemented.
        n_clusters : int
            Number of clusters for KMeans.
        random_state : int
            Random state for reproducibility.
        kwargs : dict
            Additional keyword arguments passed to the clustering algorithm.
        """
        self.method = method.lower()
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.kwargs = kwargs
        self.model = None

    def fit(self, df, exclude_cols='site_name'):
        """
        Fit the clustering model to the DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame of normalized indices (numeric values only).

        Returns
        -------
        pd.Series
            Cluster labels for each row in the DataFrame.
        """
        df = df.copy()

        if exclude_cols is None:
            exclude_cols = []

        # Select only numeric columns, excluding any in exclude_cols
        numeric_cols = [col for col in df.select_dtypes(include=["number"]).columns if col not in exclude_cols]

        X = df[numeric_cols].values

        if self.method == "kmeans":
            self.model = cluster.KMeans(
                n_clusters=self.n_clusters,
                random_state=self.random_state,
                **self.kwargs
            )
        elif self.method == "agglomerative":
            self.model = cluster.AgglomerativeClustering(
                n_clusters=self.n_clusters,
                **self.kwargs
            )
        elif self.method == "spectral":
            self.model = cluster.SpectralClustering(
                n_clusters=self.n_clusters,
                **self.kwargs
            )
        else:
            raise NotImplementedError(f"Clustering method '{self.method}' is not implemented yet.")

        labels = self.model.fit_predict(X)

        # Insert cluster as second column
        df.insert(1, "cluster", labels)
        return df


    def get_model(self):
        """Return the fitted clustering model (e.g., KMeans instance)."""
        return self.model


def run_pca(df, exclude_cols=['site_name'], n_components=0.95):
    """
    Run PCA on a DataFrame, keeping site_name as first column
    and inserting cluster as second column if it exists.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with numeric features + site_name + cluster
    exclude_cols : list
        Columns to exclude from PCA (default keeps site_name and cluster)
    n_components : int, float, or None
        Number of components for PCA.
        - int: exact number
        - float (0 < n < 1): proportion of variance to retain
        - None: keep all components

    Returns
    -------
    pd.DataFrame
        DataFrame with site_name, cluster, and PCA components
    """
    df = df.copy()

    # Identify numeric cols for PCA
    numeric_cols = [
        col for col in df.select_dtypes(include=["number"]).columns
        if col not in exclude_cols
    ]
    X = df[numeric_cols].values

    # Fit PCA
    pca = PCA(n_components=n_components, random_state=42)
    X_pca = pca.fit_transform(X)

    # Build PCA DataFrame
    pca_cols = [f"PC{i+1}" for i in range(X_pca.shape[1])]
    pca_df = pd.DataFrame(X_pca, columns=pca_cols, index=df.index)

    # Rebuild final DataFrame
    out_df = pd.concat([df[["site_name"]], pca_df], axis=1)

    # Print explained variance info
    print("Number of components kept:", pca.n_components_)
    print("Explained variance ratio per component:", pca.explained_variance_ratio_)
    print("Total variance explained:", pca.explained_variance_ratio_.sum())

    return out_df


def gap_statistic(X, num_clusters, n_refs=10, random_state=42):
    np.random.seed(random_state)
    gaps = []
    for k in num_clusters:
        # Fit to real data
        km = cluster.KMeans(n_clusters=k, random_state=random_state)
        km.fit(X)
        Wk = km.inertia_

        # Reference dispersions
        ref_inertias = []
        for _ in range(n_refs):
            X_ref = np.random.uniform(
                np.min(X, axis=0),
                np.max(X, axis=0),
                size=X.shape
            )
            km_ref = cluster.KMeans(n_clusters=k, random_state=random_state)
            km_ref.fit(X_ref)
            ref_inertias.append(km_ref.inertia_)

        gap = np.mean(np.log(ref_inertias)) - np.log(Wk)
        gaps.append(gap)
    return gaps

if __name__ == "__main__":
    ni_df = pd.read_csv('normalized_indices.csv')
    exclude_cols = ['site_name']
    numeric_cols = [col for col in ni_df.select_dtypes(include=["number"]).columns if col not in exclude_cols]
    X = ni_df[numeric_cols].values

    # Run PCA before clustering
    pca_df = run_pca(ni_df, exclude_cols=['site_name', 'cluster'], n_components=0.9)

    method = 'spectral'
    num_clusters = list(range(2, 13))
    inertia = []
    sil_score = []
    dbi_score = []
    for num in num_clusters:
        clusterer = Clusterer(method=method, n_clusters=num)

        # Fit on raw data
        # c_df = clusterer.fit(ni_df)

        # Fit on PCA-transformed data
        c_df = clusterer.fit(pca_df)

        c_df.to_csv(f'{num}_clusters.csv', index=False)
        model = clusterer.get_model()

        # Inertia only for KMeans
        if method == "kmeans":
            inertia.append(model.inertia_)

        # Compute silhouette score
        labels = c_df['cluster'].values
        sil_score.append(silhouette_score(X, labels))
        # Davies-Bouldin Index
        dbi_score.append(davies_bouldin_score(X, labels))

    # Plot results
    if method == "kmeans":
        plt.figure(figsize=(18, 5))

        # Elbow plot (only for kmeans)
        plt.subplot(1, 3, 1)
        plt.plot(num_clusters, inertia, 'bo-')
        plt.xlabel('Number of clusters')
        plt.ylabel('Inertia')
        plt.title('Elbow Method')

        # Silhouette score
        plt.subplot(1, 3, 2)
        plt.plot(num_clusters, sil_score, 'ro-')
        plt.xlabel('Number of clusters')
        plt.ylabel('Silhouette Score')
        plt.title('Silhouette Analysis')

        # Davies-Bouldin
        plt.subplot(1, 3, 3)
        plt.plot(num_clusters, dbi_score, 'go-')
        plt.xlabel('Number of clusters')
        plt.ylabel('Davies-Bouldin Index')
        plt.title('Davies-Bouldin Index (Lower is Better)')

    else:
        plt.figure(figsize=(12, 5))

        # Silhouette score
        plt.subplot(1, 2, 1)
        plt.plot(num_clusters, sil_score, 'ro-')
        plt.xlabel('Number of clusters')
        plt.ylabel('Silhouette Score')
        plt.title('Silhouette Analysis')

        # Davies-Bouldin
        plt.subplot(1, 2, 2)
        plt.plot(num_clusters, dbi_score, 'go-')
        plt.xlabel('Number of clusters')
        plt.ylabel('Davies-Bouldin Index')
        plt.title('Davies-Bouldin Index (Lower is Better)')

    plt.tight_layout()
    plt.show()

