"""Load and save catchments and HUC12 data to parquet"""

import geopandas as gpd
import pandas as pd





GDB = r'E:\Basin_Project\NHD\NHD_all\NHDV2_MIHMS.gdb'
HUC12_FEATURE = 'HUC12_final'
CATCHMENTS_FEATURE = r'Catchments_ms'

# --- Catchments ---
catchments = gpd.read_file(r'E:\Basin_Project\NHD\NHD_all\shapefiles\catchments_final.shp')
catchments.columns = catchments.columns.str.lower()
print(catchments.columns)

catchment_columns = ['comid', 'tocomid', 'huc12', 'ismainstem', 'geometry']
subset_catchments = catchments[catchment_columns].copy()

# Convert to numeric first to handle float strings, then to Int64 (nullable)
for col in ['comid', 'tocomid', 'huc12', 'ismainstem']:
    subset_catchments[col] = pd.to_numeric(subset_catchments[col], errors='coerce').astype('Int64')

subset_catchments.to_parquet('V2_Catchments.parquet', index=False)
print("Catchments saved:", subset_catchments.dtypes)


# --- HUC12 (with geometry) ---
huc12 = gpd.read_file(GDB, layer=HUC12_FEATURE, engine='pyogrio')
huc12.columns = huc12.columns.str.lower()

huc12_columns = ['huc12', 'tohuc', 'geometry']
subset_huc12 = huc12[huc12_columns].copy()

# Convert only the non-geometry columns
for col in ['huc12', 'tohuc']:
    subset_huc12[col] = pd.to_numeric(subset_huc12[col], errors='coerce').astype('Int64')

subset_huc12.to_parquet('HUC12.parquet', index=False)
print("HUC12 saved:", subset_huc12.dtypes)
