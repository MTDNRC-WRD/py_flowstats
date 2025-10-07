import os

import pandas as pd

DIRECTORY = r'ts\ts_prep'
SITE_LIST = ['40B_06000.csv', '76HB_01000.csv', '76HB_09600.csv', '76M_01100.csv']


def join_dataframe(q_file, p_file):
    try:
        q_df = pd.read_csv(q_file, index_col=0, parse_dates=True, encoding='utf-8')
        p_df = pd.read_csv(p_file, index_col=0, parse_dates=True, encoding='utf-8')
    except FileNotFoundError:
        print(f"Error: The file '{q_file} or {p_file}' was not found.")

    p_df = p_df.reindex(q_df.index)
    merged_df = pd.merge(q_df, p_df, left_index=True, right_index=True, how='inner')

    return merged_df


if __name__ == '__main__':

    for file_name in SITE_LIST:
        q_series = os.path.join(DIRECTORY, file_name)
        prism_series = os.path.join(DIRECTORY, f'{file_name.split('.')[0]}_prism.csv')
        df_merged = join_dataframe(q_series, prism_series)
        df_merged.to_csv(os.path.join('ts', f'{file_name.split('.')[0]}_joined.csv'))
