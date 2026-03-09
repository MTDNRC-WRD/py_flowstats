import geopandas as gpd
import pandas as pd
from simpledbf import Dbf5
from shapely.geometry import MultiLineString

gdb1 = r'E:\Basin_Project\NHD\NHDPlusV21_CO_14_NHDSnapshot_07\NHDPlusCO\NHDPlus14\NHDSnapshot\Hydrography\NHDFlowline.shp'
gdb2 = r'E:\Basin_Project\NHD\NHDPlusV21_MS_10U_NHDSnapshot_07\NHDPlusMS\NHDPlus10U\NHDSnapshot\Hydrography\NHDFlowline.shp'
gdb3 = r'E:\Basin_Project\NHD\NHDPlusV21_PN_17_NHDSnapshot_08\NHDPlusPN\NHDPlus17\NHDSnapshot\Hydrography\NHDFlowline.shp'
# fc_name = 'NHDFlowline'

dbf1_path = r'E:\Basin_Project\NHD\NHDPlusV21_CO_14_NHDPlusAttributes_10\NHDPlusCO\NHDPlus14\NHDPlusAttributes\PlusFlowlineVAA.dbf'
dbf2_path = r'E:\Basin_Project\NHD\NHDPlusV21_MS_10U_NHDPlusAttributes_10\NHDPlusMS\NHDPlus10U\NHDPlusAttributes\PlusFlowlineVAA.dbf'
dbf3_path = r'E:\Basin_Project\NHD\NHDPlusV21_PN_17_NHDPlusAttributes_10\NHDPlusPN\NHDPlus17\NHDPlusAttributes\PlusFlowlineVAA.dbf'

gdb_out    = r'E:\Basin_Project\NHD\NHD_all\NHDV2_MIHMS.gdb'
fc_out_name = 'NHDall'

# ── 1. Load flowlines ─────────────────────────────────────────────────────────
print("Loading flowlines...")
gdf1 = gpd.read_file(gdb1, engine='pyogrio')
gdf2 = gpd.read_file(gdb2, engine='pyogrio')
gdf3 = gpd.read_file(gdb3, engine='pyogrio')
print(f"  HUC14 : {len(gdf1):,} flowlines")
print(f"  HUC10U: {len(gdf2):,} flowlines")
print(f"  HUC17 : {len(gdf3):,} flowlines")

# ── 2. Load VAA tables ────────────────────────────────────────────────────────
print("\nLoading VAA tables...")
df1 = Dbf5(dbf1_path).to_dataframe()
df2 = Dbf5(dbf2_path).to_dataframe()
df3 = Dbf5(dbf3_path).to_dataframe()

for df in [df1, df2, df3]:
    df.columns = df.columns.str.strip()

# Verify ComID is present in both flowlines and VAA tables
for name, gdf, df in [('HUC14', gdf1, df1), ('HUC10U', gdf2, df2), ('HUC17', gdf3, df3)]:
    assert 'ComID' in gdf.columns or 'COMID' in gdf.columns, \
        f"{name} flowlines missing ComID column. Found: {gdf.columns.tolist()}"
    assert 'ComID' in df.columns or 'COMID' in df.columns, \
        f"{name} VAA table missing ComID column. Found: {df.columns.tolist()}"

# Normalise ComID column name to 'ComID' in VAA tables
for df in [gdf1, gdf2, gdf3]:
    if 'COMID' in df.columns and 'ComID' not in df.columns:
        df.rename(columns={'COMID': 'ComID'}, inplace=True)

# ── 3. Join VAA on ComID (unique per flowline) ────────────────────────────────
print("\nJoining VAA on ComID...")
before1, before2, before3 = len(gdf1), len(gdf2), len(gdf3)

gdf1_joined = gdf1.merge(df1, on='ComID', how='left')
gdf2_joined = gdf2.merge(df2, on='ComID', how='left')
gdf3_joined = gdf3.merge(df3, on='ComID', how='left')

# Verify no duplicates were introduced by the join
for name, before, after in [('HUC14', before1, len(gdf1_joined)),
                              ('HUC10U', before2, len(gdf2_joined)),
                              ('HUC17', before3, len(gdf3_joined))]:
    if after != before:
        print(f"  WARNING: {name} row count changed {before:,} -> {after:,} "
              f"({after - before:+,}) — ComID may not be unique in VAA table")
    else:
        print(f"  {name}: {after:,} rows ✓ (no duplicates introduced)")

# ── 4. Concatenate ────────────────────────────────────────────────────────────
print("\nConcatenating regions...")
merged_gdf = gpd.GeoDataFrame(
    pd.concat([gdf1_joined, gdf2_joined, gdf3_joined], ignore_index=True),
    crs=gdf1.crs
)
print(f"  Total merged: {len(merged_gdf):,} flowlines")
# Force all geometries to MultiLineString
merged_gdf['geometry'] = [MultiLineString([feature]) if feature.geom_type == 'LineString' else feature for feature in merged_gdf.geometry]

# Final duplicate ComID check across regions
dup_comids = merged_gdf['ComID'].duplicated().sum()
if dup_comids > 0:
    print(f"  WARNING: {dup_comids:,} duplicate ComIDs across regions — check for overlapping HUC boundaries")
else:
    print(f"  ✓ All ComIDs unique across regions")

# ── 5. Export ─────────────────────────────────────────────────────────────────
print("\nExporting...")
merged_gdf.to_file(gdb_out, layer=fc_out_name, driver='OpenFileGDB', engine='pyogrio')

# ── 6. Verify ─────────────────────────────────────────────────────────────────
print("\nVerifying output...")
gdf_f = gpd.read_file(gdb_out, layer=fc_out_name, engine='pyogrio')
print(f"  Feature count : {len(gdf_f):,}")
print(f"  Columns       : {gdf_f.columns.tolist()}")