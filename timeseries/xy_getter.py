import pandas as pd

target_gages = pd.read_csv('new_gages.csv')
all_gages = pd.read_csv('gage_locations.csv')

target_gage_locations = pd.merge(target_gages, all_gages, on='gages', how='left')
# 'on=' specifies the common column to merge on.
# 'how=' specifies the type of merge.
# 'left' merge keeps all rows from df1 and adds matching data from df2.
# If an ID from df1 is not in df2, the new columns from df2 will have NaN values.

target_gage_locations.to_csv('new_gages_xy.csv')
