import os

import matplotlib.pyplot as plt
import pandas as pd

from LinAR_functions import interpolate_linar

LOOP_MODE = True

INPUT_FOLDER = 'ts_data'
OUTPUT_FOLDER = 'ts_linar'
CSV_PATH = os.path.join(INPUT_FOLDER, '06169500.csv')
CSV_OUTPUT = os.path.join(OUTPUT_FOLDER, '06169500.csv')


def linar_interpolate(file_path):
    filepath = file_path  # INSERT YOUR FILE NAME.
    # column_dates = ''  # INSERT THE HEADER OF THE DATES COLUMN.
    column_id = 'q'  # INSERT THE HEADER OF THE COLUMN WITH OBSERVATIONS TO BE INTERPOLATED.
    # separator = ','  # DEFAULT DATA SEPARATOR = ';', IF IT IS DIFFERENT (E.G. ',' OR ' ') PLEASE UPDATE THIS VARIABLE.
    learn_len = 100  # INSERT THE SIZE OF THE TRAIN DATA FOR THE AUTOREGRESSION. DEFAULT = 100.
    max_lags = 10  # INSERT THE MAXIMUM NUMBER OF AUTOREGRESSIVE LAGS INCLUDED IN THE MODEL. DEFAULT = 10.
    max_linear = 14  # INSERT THE MAXIMUM GAP SIZE TO BE LINEARLY INTERPOLATED. DEFAULT = 72.
    max_linar = 14  # INSERT THE MAXIMUM GAP SIZE TO BE INTERPOLATED WITH THE LINAR METHOD. RECOMMENDED = 14.
    sig_adf = 0.01  # THE SIGNIFICANCE LEVEL FOR THE ADF TEST. DEFAULT = 0.05.
    sig_ft = 0.01  # THE SIGNIFICANCE LEVEL FOR THE F TEST. DEFAULT = 0.05.
    number_of_diffs = 2  # NUMBER OF DIFFERENCINGS ALLOWED IN THE WHILE LOOP. DEFAULT = 2.
    output_file = os.path.join(OUTPUT_FOLDER, filepath)  # INSERT YOUR OUTPUT FILE NAME

    df = pd.read_csv(filepath, index_col=0, parse_dates=True)
    itpd = interpolate_linar(df, column_id, learn_len, max_lags, max_linear, max_linar, sig_adf, sig_ft,
                             number_of_diffs)

    # fig, ax = plt.subplots()
    # ax.plot(itpd, color='red', label='interpolated')
    # ax.plot(df[column_id], color='grey', linewidth=1.5, label='true observations')
    # ax.legend()
    # plt.show()

    return itpd


if __name__ == '__main__':

    if LOOP_MODE:
        all_files = os.listdir(INPUT_FOLDER)
        for file_name in all_files:
            df_intr = linar_interpolate(os.path.join(INPUT_FOLDER, file_name))
            print(f"\n{file_name}")
            df_intr.to_csv(os.path.join(OUTPUT_FOLDER, file_name))

    else:
        df_intr = linar_interpolate(CSV_PATH)
        print(f"\n{CSV_PATH}")
        df_intr.to_csv(CSV_OUTPUT)
