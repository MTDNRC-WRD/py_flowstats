import os
import pandas as pd

# path to your folder
folder_path = r'C:\Users\CND367\Documents\Python_Scripts\Basin_Project\timeseries\timeseries_interpolated'

# get only .csv files, strip extension, and remove 'interpolated_' prefix if present
files = [
    os.path.splitext(f)[0].replace('interpolated_', '')
    for f in os.listdir(folder_path)
    if f.lower().endswith('.csv')
]

# create dataframe
df = pd.DataFrame(files, columns=['gage'])
df.to_csv('gage_list.csv')
print(df)