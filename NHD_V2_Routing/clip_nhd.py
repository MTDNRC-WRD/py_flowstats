import geopandas as gpd

gdb_NHD    = r'E:\Basin_Project\NHD\NHD_all\NHDV2_MIHMS.gdb'
fc_NHD     = 'NHDall'
fc_out     = 'Flowlines_Filtered'
gdb_regions = r'E:\Basin_Project\StreamClassCommons.gdb'
fc_regions  = 'HUC12_EntireStudyArea'

# Load data
print("Loading features...")
flowlines_all = gpd.read_file(gdb_NHD, layer=fc_NHD, engine='pyogrio')
print("flowlines loaded")
catchments = gpd.read_file(gdb_regions, layer=fc_regions, engine='pyogrio')
print("catchments loaded")

# Align CRS
if flowlines_all.crs != catchments.crs:
    print("Aligning CRS...")
    catchments = catchments.to_crs(flowlines_all.crs)

# Spatial join — inner keeps only flowlines that intersect a catchment
print("Performing spatial join...")
filtered_flowlines = gpd.sjoin(flowlines_all, catchments, how="inner", predicate="intersects")

# Drop join artifacts and deduplicate (flowline may intersect multiple catchments)
filtered_flowlines = filtered_flowlines.drop(columns=['index_right'])
filtered_flowlines = filtered_flowlines.drop_duplicates(subset='ComID').reset_index(drop=True)

# Clean geometries — keep only line types
print("Cleaning geometries...")
filtered_flowlines = filtered_flowlines[
    filtered_flowlines.geometry.type.isin(['LineString', 'MultiLineString'])
].reset_index(drop=True)

print(f"Exporting {len(filtered_flowlines)} features...")
try:
    filtered_flowlines.to_file(
        gdb_NHD,
        layer=fc_out,
        driver="OpenFileGDB",
        engine='pyogrio',
        geometry_type="LineString"
    )
    print("Success!")
except Exception as e:
    print(f"Export failed: {e}")

print("Process complete.")