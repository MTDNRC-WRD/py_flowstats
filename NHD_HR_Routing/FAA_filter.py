"""
One-time export: filter national NHDPlusFlow VAA to local flowlines
and save as parquet for fast future loading.
"""

import geopandas as gpd
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
GDB_PATH        = r'E:\Basin_Project\NHDplusHR\NHDplusHR.gdb'
FLOWLINE_LAYER  = 'HR_flowlines_clip'
VAA_GDB         = r'E:\Basin_Project\NHDPlus_H_National_Release_2_GDB\NHDPlus_H_National_Release_2_GDB.gdb'
VAA_LAYER       = 'NHDPlusFlow'
OUTPUT_PARQUET = r'E:\Basin_Project\NHDplusHR\NHDPlusFlow_local.parquet'

CHUNK_SIZE = 500_000

# ── 1. Load local NHDPlusIDs ──────────────────────────────────────────────────
print("Loading local flowline IDs...")
flowlines = gpd.read_file(GDB_PATH, layer=FLOWLINE_LAYER)
flowlines.columns = flowlines.columns.str.lower()
flowlines['nhdplusid'] = pd.to_numeric(flowlines['nhdplusid'], errors='coerce').astype('Int64')
local_ids = set(flowlines['nhdplusid'].dropna())
print(f"  Local NHDPlusIDs: {len(local_ids):,}")

# ── 2. Load full VAA and filter in chunks ─────────────────────────────────────
print(f"\nLoading and filtering VAA table: {VAA_LAYER}")
print(f"  (this will take a few minutes on 34M rows...)")

# Read full table — pyogrio loads GDB tables without geometry
import pyogrio

vaa_full = pyogrio.read_dataframe(VAA_GDB, layer=VAA_LAYER)
vaa_full.columns = vaa_full.columns.str.lower()
print(f"  Loaded {len(vaa_full):,} total VAA records")

# Filter to local IDs
vaa_full['fromnhdpid'] = pd.to_numeric(vaa_full['fromnhdpid'], errors='coerce').astype('Int64')
vaa_full['tonhdpid'] = pd.to_numeric(vaa_full['tonhdpid'], errors='coerce').astype('Int64')

vaa_local = vaa_full[vaa_full['fromnhdpid'].isin(local_ids)].copy()
print(f"  Filtered to local: {len(vaa_local):,} records")

# Sanity check
print(f"\n  Sample fromnhdpid: {vaa_local['fromnhdpid'].head(3).tolist()}")
print(f"  Sample tonhdpid:   {vaa_local['tonhdpid'].head(3).tolist()}")
overlap = set(vaa_local['fromnhdpid'].dropna()) & local_ids
print(f"  Overlap with local flowlines: {len(overlap):,}  (should be close to {len(local_ids):,})")

# ── 3. Export to parquet ──────────────────────────────────────────────────────
print(f"\nExporting to parquet: {OUTPUT_PARQUET}")
vaa_local.to_parquet(OUTPUT_PARQUET, index=False)
size_mb = Path(OUTPUT_PARQUET).stat().st_size / 1024 / 1024
print(f"  Done. File size: {size_mb:.1f} MB")

print(f"""
── Summary ──────────────────────────────────────────────────
  National VAA rows : {len(vaa_full):,}
  Local VAA rows    : {len(vaa_local):,}
  Output            : {OUTPUT_PARQUET}

  To load in future runs:
  vaa_local = pd.read_parquet(r'{OUTPUT_PARQUET}')
─────────────────────────────────────────────────────────────
""")