import os
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


def normalize_dataframe(df, ignore_cols=None):
    """
       Normalize all numeric columns of a pandas DataFrame using MinMaxScaler (0–1 range),
       while ignoring specific columns.

       Parameters
       ----------
       df : pd.DataFrame
           Input DataFrame with numeric features.
       ignore_cols : list of str, optional
           List of column names to ignore during normalization.

       Returns
       -------
       pd.DataFrame
           Normalized DataFrame with same columns and index.
    """

    if ignore_cols is None:
        ignore_cols = []

    scaler = MinMaxScaler()
    numeric_cols = [
        col for col in df.select_dtypes(include=["number"]).columns
        if col not in ignore_cols
    ]
    df_scaled = df.copy()
    df_scaled[numeric_cols] = scaler.fit_transform(df[numeric_cols])
    print("Indices Normalized")
    return df_scaled




if __name__ == "__main__":
    parent_directory = os.path.dirname(os.getcwd())
    all_stats_path = os.path.join(parent_directory, 'flow_stats', 'output', 'compiled_all_sites.csv')
    all_stats_df = pd.read_csv(all_stats_path)

    ignore = ['site_name', 'water_year']
    df = normalize_dataframe(all_stats_df, ignore)
    df.to_csv('normalized_indices.csv')
