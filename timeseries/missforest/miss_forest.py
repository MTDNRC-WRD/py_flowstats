import os

import pandas as pd

from missforest import MissForest
import matplotlib.pyplot as plt

LOOP_MODE = False
PLOT = True

CSV_PATH = r"C:\Users\CND367\Downloads\georgetownlake_elevation_trainingdata_cleaned_bm_em.csv"
CSV_OUTPUT = r'C:\Users\CND367\Downloads\georgetownlake_elevation_forest4.csv'

INPUT_FOLDER = 'ts'
OUTPUT_FOLDER = 'ts_interpolated'


def missforest_fill(file_path):

    try:
        ts_df = pd.read_csv(file_path, index_col=0, parse_dates=True, encoding='utf-8')
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")

    # ts_df['dayofyear'] = ts_df.index.dayofyear
    # ts_df['month'] = ts_df.index.month
    # ts_df['q_lag1'] = ts_df['q'].shift(1)#looks at prior day q
    # ts_df['q_lag2'] = ts_df['q'].shift(2)#looks at q 2 days ago
    # ts_df['q_lead1'] = ts_df['q'].shift(-1)#looks at next day q
    # ts_df['q_lead2'] = ts_df['q'].shift(-2)#looks at q 2 days from now
    # ts_df['q_rolling_mean_7d'] = ts_df['q'].rolling(window=7, min_periods=1).mean()
    # ts_df['q_rolling_std_7d'] = ts_df['q'].rolling(window=7, min_periods=1).std()

    # ts_df = ts_df.drop('tmean_c', axis=1)

    # print("DataFrame passed to MissForest:")
    # print(ts_df.head())
    # print("\nCollumn Names:", ts_df.columns)
    # print("\nShape of DataFrame before imputation:", ts_df.shape)
    # print("\nDataFrame Info:")
    # ts_df.info()
    # print("\nDatatypes:", ts_df.dtypes)
    # print("\nNumber of NaNs per column:")
    # print(ts_df.isna().sum())
    # print("\nAre there any columns with non-NaN values?", any(ts_df.count() > 0))

    ts_df = ts_df.set_index('datetime')
    categorical_cols = []
    imputer = MissForest(categorical=categorical_cols)
    df_imputed = imputer.fit_transform(ts_df)



    # Visualize Results
    if PLOT:
        plt.figure(figsize=(18, 8))
        plt.plot(ts_df.index, ts_df['elevation'], 'o-', markersize=4, label='Original Data (with gaps)',
                 alpha=0.7)
        plt.plot(df_imputed.index, df_imputed['elevation'], 'r-', label='Imputed Data', alpha=0.8)

        # Highlight the imputed points specifically
        imputed_points = df_imputed[ts_df['elevation'].isna()]
        plt.scatter(imputed_points.index, imputed_points['elevation'], color='green', marker='X', s=100, zorder=5,
                    label='Imputed Points')

        plt.title('Discharge Time Series: Original vs. Imputed Data Gaps')
        plt.xlabel('Date')
        plt.ylabel('Discharge (cfs)')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show(block=True)


    return df_imputed


if __name__ == '__main__':

    if LOOP_MODE:
        all_files = os.listdir(INPUT_FOLDER)
        for file_name in all_files:
            df_fill = missforest_fill(os.path.join(INPUT_FOLDER, file_name))
            print(f"\n{file_name}")
            df_fill.to_csv(os.path.join(OUTPUT_FOLDER, file_name))

    else:
        df_fill = missforest_fill(CSV_PATH)
        print(f"\n{CSV_PATH}")
        df_fill.to_csv(CSV_OUTPUT)
