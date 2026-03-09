import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import fiona

GDB_PATH        = r'E:\Basin_Project\NHDplusHR\NHDplusHR.gdb'
FLOWLINE_LAYER  = 'HR_flowlines_clip'
VAA_LAYER       = r'E:\Basin_Project\NHDplusHR\NHDPlusFlow_local.parquet'
OUTPUT_GDB      = r'E:\Basin_Project\NHDplusHR\NHDplusHR.gdb'
OUTPUT_FEATURE  = 'Flowlines_Routed'
OUTPUT_CSV      = r'nhdplusid_routing.csv'
TERMINAL_CSV    = r'terminal_flowlines.csv'
ORPHAN_CSV      = r'orphans.csv'


MAX_ORPHAN_HOPS = 20

def to_pyint(val):
    try:
        return None if pd.isna(val) else int(val)
    except (TypeError, ValueError):
        return None
# ── 1. Confirm available layers ───────────────────────────────────────────────
print("Layers in GDB:")
for l in fiona.listlayers(GDB_PATH):
    print(f"  {l}")

# ── 2. Load flowlines ─────────────────────────────────────────────────────────
print("\nLoading HR flowlines...")
flowlines = gpd.read_file(GDB_PATH, layer=FLOWLINE_LAYER)
flowlines.columns = flowlines.columns.str.lower()
print(f"  Flowline columns: {flowlines.columns.tolist()}")
print(f"  Loaded {len(flowlines):,} flowlines | CRS: {flowlines.crs}")
print(f"\n  MainPath distribution:\n{flowlines['mainpath'].value_counts().to_string()}")
print(f"\n  InNetwork distribution:\n{flowlines['innetwork'].value_counts().to_string()}")
print(f"\n  FType distribution:\n{flowlines['ftype'].value_counts().to_string()}")
print(f"\n  Divergence distribution:\n{flowlines['divergence'].value_counts().to_string()}")


# ── 3. Load and clean VAA ─────────────────────────────────────────────────────
print(f"\nLoading VAA flow table...")
vaa = pd.read_parquet(VAA_LAYER)
vaa.columns = vaa.columns.str.lower()
print(f"  Loaded {len(vaa):,} VAA records")
print(f"  VAA columns: {vaa.columns.tolist()}")

# HR NHDPlusFlow table uses 'fromnhdpid' / 'tonhdpid'
id_col = 'fromnhdpid'
to_col = 'tonhdpid'

vaa[id_col] = pd.to_numeric(vaa[id_col], errors='coerce').astype('Int64')
vaa[to_col] = pd.to_numeric(vaa[to_col], errors='coerce').astype('Int64')

# Clip VAA to local flowlines to eliminate cross-VPU duplicates
local_ids = set(flowlines['nhdplusid'].dropna().astype(int))
vaa_local = vaa[vaa[id_col].isin(local_ids)].copy()
print(f"  National VAA records : {len(vaa):,}")
print(f"  Local VAA records    : {len(vaa_local):,}")

# Deduplicate
dupes = vaa_local[id_col].duplicated().sum()
print(f"  Duplicate fromnhdpid after clip: {dupes:,}")
if dupes > 0:
    vaa_local = (vaa_local.sort_values(to_col, ascending=False)
                          .drop_duplicates(subset=[id_col], keep='first'))
    print(f"  After dedup: {len(vaa_local):,}")

# Build local graph
full_graph = {
    to_pyint(k): to_pyint(v)
    for k, v in zip(vaa_local[id_col], vaa_local[to_col])
    if to_pyint(k) is not None
}
print(f"  Local HR graph: {len(full_graph):,} reach-to-reach pointers")

# ── 4. Enforce dendritic network via MainPath + InNetwork ─────────────────────
# This replaces prepare_nhdplus entirely for HR.
# MainPath is all 0 in this clipped dataset — unusable as a filter
# InNetwork=1 alone is sufficient for dendritic enforcement in HR
print("\nEnforcing dendritic network (InNetwork=1 only — MainPath zeroed in clip)...")

flowlines['innetwork'] = pd.to_numeric(flowlines['innetwork'], errors='coerce').fillna(0).astype(int)
flowlines['nhdplusid'] = pd.to_numeric(flowlines['nhdplusid'], errors='coerce').astype('Int64')

n_total   = len(flowlines)
dendritic = flowlines[flowlines['innetwork'] == 1].copy()

print(f"  Original flowlines      : {n_total:,}")
print(f"  Dendritic (InNetwork=1) : {len(dendritic):,}")
print(f"  Dropped                 : {n_total - len(dendritic):,}")

# Also filter by divergence to remove braids from the backbone
# divergence=1 = main channel, divergence=2 = minor braid/diversion
if 'divergence' in dendritic.columns:
    dendritic['divergence'] = pd.to_numeric(dendritic['divergence'], errors='coerce').fillna(0).astype(int)
    n_before = len(dendritic)
    dendritic = dendritic[dendritic['divergence'] != 2].copy()
    print(f"  After removing divergence=2 braids: {len(dendritic):,} (removed {n_before - len(dendritic):,})")


# ── 5. Assign ToNHDPlusID from local VAA ──────────────────────────────────────
print("\nAssigning ToNHDPlusID to dendritic reaches...")
dendritic = dendritic.merge(
    vaa_local[[id_col, to_col]].rename(columns={id_col: 'nhdplusid', to_col: 'tonhdplusid'}),
    on='nhdplusid',
    how='left'
)

dendritic['tonhdplusid'] = pd.to_numeric(dendritic['tonhdplusid'], errors='coerce')
dendritic.loc[dendritic['tonhdplusid'] == 0, 'tonhdplusid'] = pd.NA

# Null out ToNHDPlusID pointing outside local clip — boundary outlets
# Avoid pd.NA in isin() set which causes ambiguous boolean error
outside_mask = (
    dendritic['tonhdplusid'].notna() &
    ~dendritic['tonhdplusid'].astype('Int64').isin(local_ids)
)
n_boundary = outside_mask.sum()
dendritic.loc[outside_mask, 'tonhdplusid'] = pd.NA
print(f"  Boundary outlets (ToNHDPlusID outside clip): {n_boundary:,}")

n_terminals = dendritic['tonhdplusid'].isna().sum()
print(f"  Terminal reaches (no downstream in local network): {n_terminals:,}")

# ── 6. Validate dendritic structure ───────────────────────────────────────────
print("\nValidating dendritic structure...")
dup_check = dendritic.groupby('nhdplusid')['tonhdplusid'].nunique()
multi = dup_check[dup_check > 1]
if len(multi):
    print(f"  WARNING: {len(multi)} NHDPlusIDs still have multiple ToNHDPlusIDs")
else:
    print("  ✓ All NHDPlusIDs map to a single ToNHDPlusID")

# ── 7. Re-route orphans (divergence=2) via direct VAA lookup ──────────────────
print("\nIdentifying orphans...")
dendritic_ids = set(dendritic['nhdplusid'].dropna().astype(int))
all_ids       = set(flowlines['nhdplusid'].dropna().astype(int))
orphan_ids    = all_ids - dendritic_ids
print(f"  Orphan reaches: {len(orphan_ids):,}")

# Direct VAA lookup for orphans — no walking, just one hop
orphan_vaa = vaa_local[vaa_local[id_col].isin(orphan_ids)][
    [id_col, to_col]
].copy()
orphan_vaa.columns = ['nhdplusid', 'tonhdplusid']
orphan_vaa['nhdplusid']   = orphan_vaa['nhdplusid'].apply(to_pyint)
orphan_vaa['tonhdplusid'] = orphan_vaa['tonhdplusid'].apply(to_pyint)

# Ensure each orphan maps to exactly one tonhdplusid
dupes = orphan_vaa['nhdplusid'].duplicated().sum()
if dupes:
    print(f"  {dupes} orphans have multiple VAA entries — keeping highest tonhdplusid")
    orphan_vaa = (orphan_vaa.sort_values('tonhdplusid', ascending=False)
                            .drop_duplicates(subset=['nhdplusid'], keep='first'))

# Flag orphans whose tonhdplusid lands outside the local network
outside = ~orphan_vaa['tonhdplusid'].isin(all_ids | {None})
print(f"  Orphans routing outside clip (boundary): {outside.sum():,}")

# Null out boundary ones — they become terminals
orphan_vaa.loc[outside, 'tonhdplusid'] = None

n_found    = orphan_vaa['tonhdplusid'].notna().sum()
n_terminal = orphan_vaa['tonhdplusid'].isna().sum()
n_missing  = len(orphan_ids) - len(orphan_vaa)   # orphans with no VAA entry at all

print(f"  Orphans re-routed    : {n_found:,}")
print(f"  Orphans → terminals  : {n_terminal:,}")
print(f"  Orphans missing VAA  : {n_missing:,}")
orphan_vaa['source'] = 'rerouted'
orphan_vaa.to_csv(ORPHAN_CSV, index=False)

# ── 8. Build full routing table ───────────────────────────────────────────────
print("\nBuilding full routing table...")
routing_dendritic         = dendritic[['nhdplusid', 'tonhdplusid']].copy()
routing_dendritic['nhdplusid']   = routing_dendritic['nhdplusid'].apply(to_pyint)
routing_dendritic['tonhdplusid'] = routing_dendritic['tonhdplusid'].apply(to_pyint)
routing_dendritic['source']      = 'dendritic'

full_routing = pd.concat([routing_dendritic, orphan_vaa], ignore_index=True)

dupes = full_routing['nhdplusid'].duplicated().sum()
if dupes:
    print(f"  WARNING: {dupes} duplicate NHDPlusIDs")
else:
    print(f"  ✓ No duplicate NHDPlusIDs")

full_routing.to_csv(OUTPUT_CSV, index=False)
print(f"  Saved: {OUTPUT_CSV}  ({len(full_routing):,} rows)")

# ── 9. Export dendritic flowlines ─────────────────────────────────────────────
print(f"\nExporting dendritic flowlines to: {OUTPUT_GDB}")
dendritic.to_file(OUTPUT_GDB, layer=OUTPUT_FEATURE, driver='OpenFileGDB', engine='pyogrio')
print("  Done.")

# ── 10. Summary ───────────────────────────────────────────────────────────────
print(f"""
── Summary ──────────────────────────────────────────────────
  Original flowlines      : {n_total:,}
  Dendritic backbone      : {len(dendritic):,}
  Total routing entries   : {len(full_routing):,}
  Terminal reaches        : {n_terminals:,}
─────────────────────────────────────────────────────────────
""")

# ── 11. Plot ──────────────────────────────────────────────────────────────────
try:
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    terminal_mask = dendritic['tonhdplusid'].isna()
    dendritic.plot(ax=ax, linewidth=0.4, color='steelblue')
    dendritic[terminal_mask].plot(ax=ax, linewidth=1.5, color='red',
                                  label=f'Terminals ({n_terminals:,})')
    ax.set_title(f'NHDPlus HR Dendritic Network ({len(dendritic):,} reaches)', fontsize=11)
    ax.axis('off')
    ax.legend(loc='lower right', fontsize=8)
    plt.tight_layout()
    plot_path = str(Path(OUTPUT_CSV).parent / 'hr_dendritic_network.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Map saved: {plot_path}")
    plt.show()
except Exception as e:
    print(f"Plot skipped: {e}")