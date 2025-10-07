import pandas as pd

old_gages_df = pd.read_csv('og_gages.csv')
new_gages_df = pd.read_csv('new_gages.csv')
# print(old_gages_df)
# print(new_gages_df)


old_list = old_gages_df['gages'].tolist()
# print(old_list)
new_list = new_gages_df['gages'].tolist()
# print(new_list)

repeats = []
for item in new_list:
    if item in old_list:
        repeats.append(item)
print(repeats)