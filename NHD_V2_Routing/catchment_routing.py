"""
NHD Catchment Routing
Joins the dendritic flowline routing table (comid -> tocomid) to NHDPlusV2
catchments via the FEATUREID field, producing a routed catchment layer.

FEATUREID in the catchments layer == COMID in the flowlines layer.
"""

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

CATCHMENT_GDB     = r'E:\Basin_Project\NHD\NHD_all\NHDV2_MIHMS.gdb'
CATCHMENT_FEATURE = 'catchments_clip'                  # NHDPlusV2 catchment layer name

ROUTING_CSV       = r'C:\Users\CND367\Documents\Python_Scripts\hydrologic_indices\NHD_V2_Routing\comid.csv'

OUTPUT_GDB        = r'E:\Basin_Project\NHD\NHD_all\NHDV2_MIHMS.gdb'
OUTPUT_FEATURE    = 'Catchments_Routed_old'

TERMINAL_CSV          = r'C:\Users\CND367\Documents\Python_Scripts\hydrologic_indices\NHD_V2_Routing\terminal_catchments.csv'
TERMINAL_FLOWLINES_CSV = r'C:\Users\CND367\Documents\Python_Scripts\hydrologic_indices\NHD_V2_Routing\terminal_flowlines.csv'

MAX_HOPS = 15

# ── 1. Load catchments ────────────────────────────────────────────────────────
print("Loading catchments...")
catchments = gpd.read_file(CATCHMENT_GDB, layer=CATCHMENT_FEATURE)
catchments.columns = catchments.columns.str.lower()
print(f"  Loaded {len(catchments):,} catchments | CRS: {catchments.crs}")

# ── 2. Load routing table ─────────────────────────────────────────────────────
print("Loading routing table...")
routing = pd.read_csv(ROUTING_CSV)
routing.columns = routing.columns.str.lower()
print(f"  Loaded {len(routing):,} routing records")

# Safe nullable int casting throughout
catchments['featureid'] = pd.to_numeric(catchments['featureid'], errors='coerce').astype('Int64')
routing['comid']        = pd.to_numeric(routing['comid'],        errors='coerce').astype('Int64')
routing['tocomid']      = pd.to_numeric(routing['tocomid'],      errors='coerce').astype('Int64')

bad_fid   = catchments['featureid'].isna().sum()
bad_comid = routing['comid'].isna().sum()
if bad_fid:   print(f"  WARNING: {bad_fid} catchments have null featureid")
if bad_comid: print(f"  WARNING: {bad_comid} routing records have null comid")

# ── 3. Build lookup structures ────────────────────────────────────────────────
print("\nBuilding lookup structures...")

# Normalise to plain Python int/None to avoid pandas Int64 type mismatches
# inside dicts and set lookups during the hop walk
def to_pyint(val):
    try:
        return None if pd.isna(val) else int(val)
    except (TypeError, ValueError):
        return None

# comid -> tocomid dict for downstream walk (plain ints, None for terminals)
routing_dict = {
    to_pyint(k): to_pyint(v)
    for k, v in zip(routing['comid'], routing['tocomid'])
    if to_pyint(k) is not None
}

# Set of COMIDs that have a real catchment polygon (plain ints)
valid_catchment_comids = set(
    int(fid) for fid in catchments['featureid'].dropna()
)

print(f"  Valid catchment COMIDs : {len(valid_catchment_comids):,}")
print(f"  Total routing COMIDs   : {len(routing_dict):,}")

# ── 4. Downstream walk function ───────────────────────────────────────────────
def resolve_tocatchment(start_comid, routing_dict, valid_comids, max_hops=10):
    """
    Walk downstream from start_comid until a valid catchment COMID is found
    or we exhaust max_hops. All inputs are plain Python int/None.
    Returns (resolved_int_or_None, hops_taken).
      hops=0  : direct tocomid was already a valid catchment
      hops>0  : resolved after N hops
      hops=-1 : genuine terminal (no tocomid) — handled before calling this
      hops=N  : hit hop limit, returns None
    """
    current = routing_dict.get(start_comid)   # None if missing

    if current is None:
        return None, -1   # terminal — shouldn't reach here but safe fallback

    for hop in range(max_hops):
        if current in valid_comids:
            return current, hop           # found a valid catchment
        current = routing_dict.get(current)   # step downstream
        if current is None:
            return None, hop + 1          # walked off the end

    return None, max_hops                 # hit hop limit

# ── 5. Resolve tocatchment for every catchment ────────────────────────────────
print(f"\nResolving tocatchment (max {MAX_HOPS} hops)...")

# Load genuine terminal flowlines from the dendritic enforcement script output.
# These are authoritative outlets — assign tocatchment=0 directly, no hopping.
print("Loading terminal flowlines...")
terminal_flowlines = pd.read_csv(TERMINAL_FLOWLINES_CSV)
terminal_flowlines.columns = terminal_flowlines.columns.str.lower()
terminal_fids = set(
    int(v) for v in pd.to_numeric(terminal_flowlines['comid'], errors='coerce').dropna()
)
print(f"  Genuine terminals loaded : {len(terminal_fids):,}  (will be assigned tocatchment=0)")

resolved_comids = []
hop_counts      = []

for fid in catchments['featureid']:
    if pd.isna(fid):
        resolved_comids.append(None)
        hop_counts.append(None)
        continue

    fid_int = int(fid)

    if fid_int in terminal_fids:
        resolved_comids.append(0)      # genuine outlet — assign 0
        hop_counts.append(-1)
    else:
        comid, hops = resolve_tocatchment(fid_int, routing_dict, valid_catchment_comids, MAX_HOPS)
        resolved_comids.append(comid)  # plain int or None
        hop_counts.append(hops)

# Build final columns — use float so None becomes NaN cleanly in the GDF
# Only catchments explicitly in terminal_fids get tocatchment=0.
# Catchments with hops==-1 that are NOT in terminal_fids have no flowline
# association at all and are treated as unresolved (NaN).
catchments['tocatchment'] = pd.array([
    float(v) if v is not None else float('nan')
    for v in resolved_comids
])
catchments['hops'] = pd.array(
    [float(v) if v is not None else float('nan') for v in hop_counts]
)

# ── 6. Report hop summary ─────────────────────────────────────────────────────
print("\nHop summary:")
total         = len(catchments)
terminals_out = (catchments['tocatchment'] == 0.0).sum()   # only explicit terminal_fids
unresolved    = catchments['tocatchment'].isna().sum()         # NaN = no flowline or hop limit hit

hop_dist = (
    catchments[catchments['hops'] >= 0]
    .groupby('hops')
    .size()
    .rename('count')
    .reset_index()
)
for _, row in hop_dist.iterrows():
    label = "direct" if row['hops'] == 0 else f"{int(row['hops'])} hop{'s' if row['hops'] > 1 else ''}"
    print(f"  {label:<12} : {row['count']:>8,}")

print(f"  {'terminals':<12} : {terminals_out:>8,}  (genuine outlets, tocatchment=0)")
print(f"  {'unresolved':<12} : {unresolved:>8,}  (no flowline association or hit {MAX_HOPS}-hop limit, tocatchment=NaN)")
print(f"  {'total':<12} : {total:>8,}")

# ── 7. Identify terminal catchments ───────────────────────────────────────────
# Terminals are now tocatchment=0 (genuine outlets) vs NaN (unresolved data gaps)
terminal_mask  = catchments['tocatchment'] == 0.0
unresolved_mask = catchments['tocatchment'].isna()
terminal_cols = [c for c in ['featureid', 'tocatchment', 'hops', 'streamorde',
                              'totdasqkm', 'reachcode'] if c in catchments.columns]
terminals = catchments[terminal_mask][terminal_cols].copy()
terminals.to_csv(TERMINAL_CSV, index=False)
print(f"\nTerminal catchments saved: {TERMINAL_CSV}")

# ── 8. Validate ───────────────────────────────────────────────────────────────
print("\nValidating catchment routing...")
dup_check = catchments.groupby('featureid')['tocatchment'].nunique()
multi = dup_check[dup_check > 1]
if len(multi) > 0:
    print(f"  WARNING: {len(multi)} FEATUREIDs map to multiple tocatchments.")
else:
    print("  ✓ All FEATUREIDs map to a single tocatchment.")

# ── 9. Export ─────────────────────────────────────────────────────────────────
print(f"\nExporting routed catchments to: {OUTPUT_GDB} | layer: {OUTPUT_FEATURE}")

# tocatchment and hops are already float (NaN=NULL in GPKG, 0.0=terminal outlet)
export = catchments.copy()
export['featureid'] = export['featureid'].astype(float)

null_count     = export['tocatchment'].isna().sum()
terminal_count = (export['tocatchment'] == 0.0).sum()
routed_count   = export['tocatchment'].notna().sum() - terminal_count

print(f"  tocatchment routed   : {routed_count:>8,}  (resolved to downstream catchment)")
print(f"  tocatchment == 0     : {terminal_count:>8,}  (genuine terminal outlets)")
print(f"  tocatchment null     : {null_count:>8,}  (unresolved after {MAX_HOPS}-hop limit)")
print(f"  total                : {len(export):>8,}")
print(f"  Output columns       : featureid, tocatchment, hops (+all original catchment fields)")

export.to_file(OUTPUT_GDB, driver="OpenFileGDB", engine='pyogrio')
print("  Done.")



# ── 10. Plot ──────────────────────────────────────────────────────────────────
try:
    print("\nplotting...")
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    catchments.plot(ax=ax, linewidth=0, edgecolor='white',
                    facecolor='steelblue', alpha=0.7)
    catchments[terminal_mask].plot(ax=ax, linewidth=0, edgecolor='white',
                                   facecolor='red', alpha=0.9,
                                   label=f'Terminals/outlets ({len(terminals):,})')
    catchments[unresolved_mask].plot(ax=ax, linewidth=0, edgecolor='white',
                                     facecolor='yellow', alpha=0.9,
                                     label=f'Unresolved ({unresolved_mask.sum():,})')

    ax.set_title(f'NHDPlusV2 Routed Catchments ({total:,} catchments)', fontsize=11)
    ax.axis('off')
    # legend(loc='lower right', fontsize=8)a

    plt.tight_layout()
    plot_path = str(Path(ROUTING_CSV).parent / 'routed_catchments.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Map saved: {plot_path}")
    plt.show()
except Exception as e:
    print(f"Plot skipped: {e}")


