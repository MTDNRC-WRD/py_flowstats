import miceforest as mf
import pandas as pd
import os
import matplotlib.pyplot as plt

LOOP_MODE = False

CSV_PATH = 'timeseries_continuous/12335100.csv'
CSV_OUTPUT = 'timeseries_interpolated/12335100.csv'

INPUT_FOLDER = 'timeseries_continuous'
OUTPUT_FOLDER = 'timeseries_interpolated'


def miceforest_fill(file_path):
    try:
        ts_df = pd.read_csv(file_path, index_col=0, parse_dates=True, encoding='utf-8')
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")

    ts_df['dayofyear'] = ts_df.index.dayofyear
    ts_df['month'] = ts_df.index.month
    ts_df['q_lag1'] = ts_df['q'].shift(1)  # looks at prior day q
    ts_df['q_lag2'] = ts_df['q'].shift(2)  # looks at q 2 days ago
    ts_df['q_lead1'] = ts_df['q'].shift(-1)  # looks at next day q
    ts_df['q_lead2'] = ts_df['q'].shift(-2)  # looks at q 2 days from now
    # ts_df['q_rolling_mean_7d'] = ts_df['q'].rolling(window=7, min_periods=1).mean()
    # ts_df['q_rolling_std_7d'] = ts_df['q'].rolling(window=7, min_periods=1).std()

    # need to store the datetime index, reset, then reload datetime index after
    og_df_index = ts_df.index
    ts_df_mice = ts_df.reset_index(drop=True)

    kernel = mf.ImputationKernel(data=ts_df_mice,
                                 num_datasets=5,
                                 random_state=42
                                 )

    # # Parameters for the underlying LightGBM models (tuning might be needed)
    # optimized_params = kernel.tune_parameters(n_estimators=300,  # More trees
    #                        max_depth=10,  # Deeper trees
    #                        learning_rate=0.05,  # Slower learning
    #                        min_child_samples=10
    #                        )

    # kernel.mice(iterations=10, variable_parameters=optimized_params, verbose=True)  # Run 10 imputation iterations
    kernel.mice(iterations=5, verbose=True)  # Run 5 imputation iterations
    df_imputed_mice = kernel.complete_data()

    df_imputed_mice = df_imputed_mice.set_index(og_df_index)
    # option to drop the added fields for imputation
    # df_imputed_mice = df_imputed_mice.drop(columns=['dayofyear', 'month'])

    # Visualize Results
    plt.figure(figsize=(18, 8))
    plt.plot(ts_df.index, ts_df['q'], 'o-', markersize=4, label='Original Data (with gaps)',
             alpha=0.7)
    plt.plot(df_imputed_mice.index, df_imputed_mice['q'], 'r-', label='Imputed Data', alpha=0.8)

    # Highlight the imputed points specifically
    imputed_points = df_imputed_mice[ts_df['q'].isna()]
    plt.scatter(imputed_points.index, imputed_points['q'], color='green', marker='X', s=100, zorder=5,
                label='Imputed Points')

    plt.title('Discharge Time Series: Original vs. Imputed Data Gaps')
    plt.xlabel('Date')
    plt.ylabel('Discharge (cfs)')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()





    return df_imputed_mice

if __name__ == '__main__':

    if LOOP_MODE:
        all_files = os.listdir(INPUT_FOLDER)
        for file_name in all_files:
            df_fill = miceforest_fill(os.path.join(INPUT_FOLDER, file_name))
            print(f"\n{file_name}")
            df_fill.to_csv(os.path.join(OUTPUT_FOLDER, file_name))

    else:
        df_fill = miceforest_fill(CSV_PATH)
        print(f"\n{CSV_PATH}")
        df_fill.to_csv(CSV_OUTPUT)
