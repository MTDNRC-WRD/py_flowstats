"""Module that compiles all upstream HUC basins.

This script uses the 'to_huc' attribute field from the NHD shapefile to identify all contributing
basins to the target basin, then merges those basins together into a single shape and adds to an output shapefile
"""

from ast import literal_eval

# import matplotlib as plt
import geopandas as gpd
import pandas as pd
from tqdm import tqdm

HUC12_MT_shp = 'shapefiles/HUC12_MT.shp'

HUC12_gdf = gpd.read_file(HUC12_MT_shp)

huc_df = HUC12_gdf[['huc12', 'tohuc']]

cont_huc_df = pd.DataFrame(columns=['basin_id', 'basin_list'])


def basin_indexer():
    """Function that outputs a .csv listing all contributing basins to a target HUC basin"""
    for index, row in tqdm(huc_df.iterrows(), total=huc_df.shape[0], desc='Processing Rows'):
        up_basins = []
        all_basins = [row['huc12']]
        tohuc_df = huc_df[huc_df['tohuc'] == row['huc12']]['huc12']
        if tohuc_df.empty:
            add_row = {'basin_id': row['huc12'], 'basin_list': all_basins}
            cont_huc_df = pd.concat([cont_huc_df, pd.DataFrame([add_row])], ignore_index=True)
        else:
            up_basins.extend(tohuc_df.tolist())
            all_basins.extend(tohuc_df.tolist())
            i = 0
            while i < len(up_basins):
                tohuc_df = huc_df[huc_df['tohuc'] == up_basins[i]]['huc12']
                i += 1
                if not tohuc_df.empty:
                    up_basins.extend(tohuc_df.tolist())
                    all_basins.extend(tohuc_df.tolist())
            add_row = {'basin_id': row['huc12'], 'basin_list': all_basins}
            cont_huc_df = pd.concat([cont_huc_df, pd.DataFrame([add_row])], ignore_index=True)

    cont_huc_df.to_csv('all_basins.csv')


def basin_compiler(basins_df: pd.DataFrame):
    """Function that outputs a .shp of merged contributing basins to a target HUC basin"""
    HUC12_comp_gdf = gpd.GeoDataFrame()
    for index, row in tqdm(basins_df.iterrows(), total=huc_df.shape[0], desc='Processing Rows'):
        ids_to_get = row['basin_list']
        # This next bit ensures the row info preserved is the target basin (i.e. most downstream)
        id_to_assign = str(row['basin_id'])
        temp_gdf = HUC12_gdf[HUC12_gdf['huc12'].isin(ids_to_get)].copy()
        temp_gdf['sort_key'] = temp_gdf['huc12'].apply(lambda x: 0 if x in id_to_assign else 1)
        temp_gdf = temp_gdf.sort_values(by=['sort_key']).reset_index(drop=True)

        temp_gdf = temp_gdf.dissolve(aggfunc='first')
        # print(HUC12_comp_gdf)
        # temp_gdf.plot()
        # plt.show()

        HUC12_comp_gdf = pd.concat([HUC12_comp_gdf, temp_gdf], ignore_index=True)
    HUC12_comp_gdf.to_file('shapefiles/HUC_12_comp.shp')


# basin_indexer()
basins_df = pd.read_csv('all_basins.csv')
basins_df['basin_list'] = basins_df['basin_list'].apply(literal_eval)
basin_compiler(basins_df)
