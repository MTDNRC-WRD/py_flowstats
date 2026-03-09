"""
NHD Plus HR Catchment Routing
Joins the dendritic flowline routing table (nhdplusid -> tonhdplusid) to
NHDPlusHR catchments via the NHDPlusID field, producing a routed catchment layer.

tocatchment values:
  > 0  : routed to downstream catchment NHDPlusID
    0  : genuine terminal outlet
   -1  : unresolved (no flowline association or hit MAX_HOPS limit)
"""

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
CATCHMENT_GDB     = r'E:\Basin_Project\NHDplusHR\NHDplusHR.gdb'
CATCHMENT_FEATURE = 'NHDPlusCatchment'

ROUTING_CSV       = r'nhdplusid_routing.csv'

OUTPUT_GDB        = r'E:\Basin_Project\NHDplusHR\NHDplusHR.gdb'
OUTPUT_FEATURE    = 'Catchments_Routed'

TERMINAL_CSV      = r'terminal_catchments.csv'

# Sentinel values
TERMINAL_VAL   =  0
UNRESOLVED_VAL = -1

MAX_HOPS = 15

def to_pyint(val):
    try:
        return None if pd.isna(val) else int(val)
    except (TypeError, ValueError):
        return None

# ── 1. Load catchments ────────────────────────────────────────────────────────
print("Loading catchments...")
catchments = gpd.read_file(CATCHMENT_GDB, layer=CATCHMENT_FEATURE)
catchments.columns = catchments.columns.str.lower()
print(f"  Loaded {len(catchments):,} catchments | CRS: {catchments.crs}")
print(f"  Catchment columns: {catchments.columns.tolist()}")

# HR catchments use 'nhdplusid' as the join key (not featureid like V2)
# confirm the key column
id_col = None
for candidate in ['nhdplusid', 'featureid', 'permanent_identifier']:
    if candidate in catchments.columns:
        id_col = candidate
        break
if id_col is None:
    raise ValueError(f"No known ID column found. Columns: {catchments.columns.tolist()}")
print(f"  Catchment ID column: '{id_col}'")

catchments[id_col] = pd.to_numeric(catchments[id_col], errors='coerce').astype('Int64')
bad = catchments[id_col].isna().sum()
if bad:
    print(f"  WARNING: {bad} catchments have null {id_col}")

# ── 2. Load routing table ─────────────────────────────────────────────────────
print("\nLoading routing table...")
routing = pd.read_csv(ROUTING_CSV)
routing.columns = routing.columns.str.lower()
routing['nhdplusid']   = pd.to_numeric(routing['nhdplusid'],   errors='coerce').astype('int64')
routing['tonhdplusid'] = pd.to_numeric(routing['tonhdplusid'], errors='coerce')
print(f"  Loaded {len(routing):,} routing records")
print(f"  Terminal entries (tonhdplusid=NaN): {routing['tonhdplusid'].isna().sum():,}")
print(f"  Source breakdown:\n{routing['source'].value_counts().to_string()}")

# ── 3. Build lookup structures ────────────────────────────────────────────────
print("\nBuilding lookup structures...")

# nhdplusid -> tonhdplusid (None for terminals)
routing_dict = {
    int(row.nhdplusid): to_pyint(row.tonhdplusid)
    for row in routing.itertuples()
}

# Terminal set — entries where tonhdplusid is NaN
terminal_ids = set(
    int(row.nhdplusid)
    for row in routing.itertuples()
    if pd.isna(row.tonhdplusid)
)

# Valid catchment IDs
valid_catchment_ids = set(
    int(x) for x in catchments[id_col].dropna()
)

print(f"  Routing dict size    : {len(routing_dict):,}")
print(f"  Terminal IDs         : {len(terminal_ids):,}")
print(f"  Valid catchment IDs  : {len(valid_catchment_ids):,}")

# Coverage check
routing_ids  = set(routing_dict.keys())
in_routing   = valid_catchment_ids & routing_ids
not_in_routing = valid_catchment_ids - routing_ids
print(f"  Catchments with routing entry    : {len(in_routing):,}")
print(f"  Catchments WITHOUT routing entry : {len(not_in_routing):,}")

# ── 4. Downstream hop walk ────────────────────────────────────────────────────
def resolve_tocatchment(start_id, routing_dict, valid_ids, max_hops):
    """
    Walk downstream from start_id until landing on a valid catchment ID.
    Returns (resolved_id or None, hops_taken)
    """
    current = routing_dict.get(start_id)
    if current is None:
        return None, -1
    for hop in range(max_hops):
        if current is None:
            return None, hop
        if current in valid_ids:
            return current, hop
        current = routing_dict.get(current)
    return None, max_hops

# ── 5. Resolve tocatchment for every catchment ────────────────────────────────
print(f"\nResolving tocatchment (max {MAX_HOPS} hops)...")

resolved = []
hops_out = []

for cid in catchments[id_col]:
    if pd.isna(cid):
        resolved.append(UNRESOLVED_VAL)
        hops_out.append(None)
        continue

    cid_int = int(cid)

    if cid_int in terminal_ids:
        resolved.append(TERMINAL_VAL)
        hops_out.append(-1)
    elif cid_int not in routing_dict:
        # Catchment has no flowline entry at all
        resolved.append(UNRESOLVED_VAL)
        hops_out.append(None)
    else:
        result, hops = resolve_tocatchment(cid_int, routing_dict, valid_catchment_ids, MAX_HOPS)
        resolved.append(result if result is not None else UNRESOLVED_VAL)
        hops_out.append(hops)

catchments['tocatchment'] = [float(v) for v in resolved]
catchments['hops']        = [float(v) if v is not None else float('nan') for v in hops_out]

# ── 6. Report ─────────────────────────────────────────────────────────────────
print("\nHop summary:")
total       = len(catchments)
n_terminals = (catchments['tocatchment'] == TERMINAL_VAL).sum()
n_unresolved = (catchments['tocatchment'] == UNRESOLVED_VAL).sum()
n_routed    = total - n_terminals - n_unresolved

hop_dist = (
    catchments[catchments['hops'] >= 0]
    .groupby('hops').size()
    .rename('count').reset_index()
)
for _, row in hop_dist.iterrows():
    label = "direct" if row['hops'] == 0 else f"{int(row['hops'])} hop{'s' if row['hops'] > 1 else ''}"
    print(f"  {label:<12} : {row['count']:>8,}")
print(f"  {'terminals':<12} : {n_terminals:>8,}  (tocatchment=0)")
print(f"  {'unresolved':<12} : {n_unresolved:>8,}  (tocatchment=-1)")
print(f"  {'routed':<12} : {n_routed:>8,}  (tocatchment>0)")
print(f"  {'total':<12} : {total:>8,}")

# ── 7. Validate ───────────────────────────────────────────────────────────────
print("\nValidating...")
dup_check = catchments.groupby(id_col)['tocatchment'].nunique()
multi = dup_check[dup_check > 1]
if len(multi):
    print(f"  WARNING: {len(multi)} IDs map to multiple tocatchments")
else:
    print("  ✓ All catchment IDs map to a single tocatchment")

# ── 8. Save terminals ─────────────────────────────────────────────────────────
terminal_mask   = catchments['tocatchment'] == TERMINAL_VAL
unresolved_mask = catchments['tocatchment'] == UNRESOLVED_VAL
terminal_cols   = [c for c in [id_col, 'tocatchment', 'hops', 'areasqkm', 'totdasqkm']
                   if c in catchments.columns]
catchments[terminal_mask][terminal_cols].to_csv(TERMINAL_CSV, index=False)
print(f"\nTerminal catchments saved: {TERMINAL_CSV}")

# ── 9. Export ─────────────────────────────────────────────────────────────────
print(f"\nExporting routed catchments to: {OUTPUT_GDB} | layer: {OUTPUT_FEATURE}")
export = catchments.copy()
export[id_col] = export[id_col].astype(float)
print(f"  tocatchment > 0  (routed)     : {n_routed:>8,}")
print(f"  tocatchment == 0 (terminals)  : {n_terminals:>8,}")
print(f"  tocatchment == -1 (unresolved): {n_unresolved:>8,}")
print(f"  total                         : {total:>8,}")
export.to_file(OUTPUT_GDB, layer=OUTPUT_FEATURE, driver='OpenFileGDB', engine='pyogrio')
print("  Done.")

# ── 10. Plot ──────────────────────────────────────────────────────────────────
try:
    print("\nPlotting...")
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    catchments.plot(ax=ax, linewidth=0, edgecolor='white', facecolor='steelblue', alpha=0.7)
    catchments[terminal_mask].plot(ax=ax, linewidth=0, edgecolor='white',
                                   facecolor='red', alpha=0.9,
                                   label=f'Terminals ({n_terminals:,})')
    catchments[unresolved_mask].plot(ax=ax, linewidth=0, edgecolor='white',
                                     facecolor='yellow', alpha=0.9,
                                     label=f'Unresolved ({n_unresolved:,})')
    ax.set_title(f'NHDPlus HR Routed Catchments ({total:,} catchments)', fontsize=11)
    ax.axis('off')
    ax.legend(loc='lower right', fontsize=8)
    plt.tight_layout()
    plot_path = str(Path(ROUTING_CSV).parent / 'hr_routed_catchments.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Map saved: {plot_path}")
    plt.show()
except Exception as e:
    print(f"Plot skipped: {e}")