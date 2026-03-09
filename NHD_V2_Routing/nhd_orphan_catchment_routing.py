"""
NHD Catchment Routing  v4
==========================
Joins the dendritic flowline routing table (comid -> tocomid) to NHDPlusV2
catchments via the FEATUREID field, producing a routed catchment layer.

FEATUREID in the catchments layer == COMID in the flowlines layer.

Resolution order for each catchment
-------------------------------------
1. Flowline routing  — featureid exists in routing CSV  → use tocomid chain
2. Terminal check    — featureid is a known outlet       → tocatchment = 0
3. Spatial fallback  — featureid not in routing CSV      → find the routed
                       neighbour catchment that shares the longest boundary
                       and inherit its tocatchment
4. Unresolved        — no neighbour found or border gap  → tocatchment = -1

tocatchment values
-------------------
  > 0  : routed to downstream catchment COMID
    0  : genuine terminal outlet
   -1  : unresolved (confirmed data gap / Canadian border)
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from shapely.ops import unary_union

# ── Paths ─────────────────────────────────────────────────────────────────────

CATCHMENT_GDB     = r'E:\Basin_Project\NHD\NHD_all\NHDV2_MIHMS.gdb'
CATCHMENT_FEATURE = 'catchments_clip'

ROUTING_CSV       = r'C:\Users\CND367\Documents\Python_Scripts\hydrologic_indices\NHD_V2_Routing\comid.csv'
TERMINAL_FLOWLINES_CSV = r'C:\Users\CND367\Documents\Python_Scripts\hydrologic_indices\NHD_V2_Routing\terminal_flowlines.csv'

OUTPUT_GDB        = r'E:\Basin_Project\NHD\NHD_all\NHDV2_MIHMS.gdb'
OUTPUT_FEATURE    = 'Catchments_Routed'

TERMINAL_CSV      = r'C:\Users\CND367\Documents\Python_Scripts\hydrologic_indices\NHD_V2_Routing\terminal_catchments.csv'
SPATIAL_CSV       = r'C:\Users\CND367\Documents\Python_Scripts\hydrologic_indices\NHD_V2_Routing\spatial_fallback.csv'

MAX_HOPS          = 15

# Sentinel values
TERMINAL_VAL   =  0
UNRESOLVED_VAL = -1

# ── Helper ────────────────────────────────────────────────────────────────────
def to_pyint(val):
    try:
        return None if pd.isna(val) else int(val)
    except (TypeError, ValueError):
        return None


def resolve_tocatchment(start_comid, routing_dict, valid_comids, max_hops):
    """Walk downstream until landing on a comid that has a catchment polygon."""
    current = routing_dict.get(start_comid)
    if current is None:
        return None, -1
    for hop in range(max_hops):
        if current is None:
            return None, hop
        if current in valid_comids:
            return current, hop
        current = routing_dict.get(current)
    return None, max_hops


# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD CATCHMENTS
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1 — Loading catchments")
print("=" * 60)
catchments = gpd.read_file(CATCHMENT_GDB, layer=CATCHMENT_FEATURE)
catchments.columns = catchments.columns.str.lower()
catchments['featureid'] = pd.to_numeric(catchments['featureid'], errors='coerce').astype('Int64')
print(f"  Loaded {len(catchments):,} catchments | CRS: {catchments.crs}")

null_fids = catchments['featureid'].isna().sum()
if null_fids:
    print(f"  WARNING: {null_fids:,} catchments have null featureid")

# ─────────────────────────────────────────────────────────────────────────────
# 2. LOAD ROUTING TABLE
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 2 — Loading routing table")
routing = pd.read_csv(ROUTING_CSV)
routing.columns = routing.columns.str.lower()
routing['comid']   = pd.to_numeric(routing['comid'],   errors='coerce').astype('Int64')
routing['tocomid'] = pd.to_numeric(routing['tocomid'], errors='coerce').astype('Int64')
print(f"  Loaded {len(routing):,} routing records")

# ─────────────────────────────────────────────────────────────────────────────
# 3. BUILD ROUTING DICT & CATCHMENT SET
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 3 — Building lookup structures")

routing_dict = {
    int(k): (int(v) if to_pyint(v) is not None else None)
    for k, v in zip(routing['comid'], routing['tocomid'])
    if to_pyint(k) is not None
}

valid_catchment_comids = {int(f) for f in catchments['featureid'].dropna()}

print(f"  Routing dict COMIDs      : {len(routing_dict):,}")
print(f"  Valid catchment COMIDs   : {len(valid_catchment_comids):,}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. LOAD TERMINAL FLOWLINES
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 4 — Loading terminal flowlines")
terminal_flowlines = pd.read_csv(TERMINAL_FLOWLINES_CSV)
terminal_flowlines.columns = terminal_flowlines.columns.str.lower()
terminal_fids = {
    int(v) for v in pd.to_numeric(terminal_flowlines['comid'], errors='coerce').dropna()
}
print(f"  Terminal flowline COMIDs : {len(terminal_fids):,}")

# ─────────────────────────────────────────────────────────────────────────────
# 5. CLASSIFY CATCHMENTS INTO ROUTING / GAP GROUPS
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 5 — Classifying catchments")

in_routing  = []   # featureid found in routing dict
gap_indices = []   # featureid NOT in routing dict — need spatial fallback

for idx, fid in zip(catchments.index, catchments['featureid']):
    if pd.isna(fid) or int(fid) not in routing_dict:
        gap_indices.append(idx)
    else:
        in_routing.append(idx)

print(f"  In routing dict (can resolve)  : {len(in_routing):,}")
print(f"  NOT in routing dict (data gap) : {len(gap_indices):,}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. RESOLVE TOCATCHMENT FOR ROUTED CATCHMENTS
# ─────────────────────────────────────────────────────────────────────────────
print(f"\nSTEP 6 — Resolving tocatchment via flowline routing (max {MAX_HOPS} hops)")

tocatchment = {}
hop_counts  = {}

for idx in in_routing:
    fid_int = int(catchments.at[idx, 'featureid'])

    if fid_int in terminal_fids:
        tocatchment[idx] = TERMINAL_VAL
        hop_counts[idx]  = -1
        continue

    downstream = routing_dict.get(fid_int)
    if downstream is None:
        # tocomid is NaN in routing table — genuine outlet
        tocatchment[idx] = TERMINAL_VAL
        hop_counts[idx]  = 0
        continue

    comid, hops = resolve_tocatchment(
        fid_int, routing_dict, valid_catchment_comids, MAX_HOPS
    )
    tocatchment[idx] = comid if comid is not None else UNRESOLVED_VAL
    hop_counts[idx]  = hops

# Pre-fill gap catchments as unresolved (spatial step may overwrite)
for idx in gap_indices:
    tocatchment[idx] = UNRESOLVED_VAL
    hop_counts[idx]  = None

# ─────────────────────────────────────────────────────────────────────────────
# 7. SPATIAL FALLBACK FOR GAP CATCHMENTS
#    For each gap catchment, find the routed neighbour it shares the longest
#    boundary with, then inherit that neighbour's tocatchment value.
#    This handles NHD data gaps where a catchment polygon exists but no
#    corresponding flowline was ever digitised (or is outside the clip extent).
# ─────────────────────────────────────────────────────────────────────────────
print(f"\nSTEP 7 — Spatial fallback for {len(gap_indices):,} gap catchments")

if gap_indices:
    # Build a set of already-routed catchment indices for fast lookup
    routed_indices = {
        idx for idx in in_routing
        if tocatchment.get(idx, UNRESOLVED_VAL) > 0
           or tocatchment.get(idx, UNRESOLVED_VAL) == TERMINAL_VAL
    }

    gap_gdf    = catchments.loc[gap_indices].copy()
    routed_gdf = catchments.loc[list(routed_indices)].copy()

    # Spatial index on routed catchments
    routed_sindex = routed_gdf.sindex

    spatial_results = []
    resolved_spatial = 0

    for idx, row in gap_gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            spatial_results.append({
                'index': idx,
                'featureid': to_pyint(row['featureid']),
                'neighbour_fid': None,
                'shared_length': 0,
                'status': 'no_geometry'
            })
            continue

        # Candidates: routed catchments whose bounding box touches this one
        candidates = list(routed_sindex.intersection(geom.bounds))
        if not candidates:
            spatial_results.append({
                'index': idx,
                'featureid': to_pyint(row['featureid']),
                'neighbour_fid': None,
                'shared_length': 0,
                'status': 'no_candidates'
            })
            continue

        # Find the candidate sharing the longest boundary
        best_length  = 0.0
        best_idx     = None
        best_fid     = None

        candidate_rows = routed_gdf.iloc[candidates]
        for c_idx, c_row in candidate_rows.iterrows():
            try:
                shared = geom.intersection(c_row.geometry)
                length = shared.length
            except Exception:
                length = 0.0
            if length > best_length:
                best_length = length
                best_idx    = c_idx
                best_fid    = to_pyint(c_row['featureid'])

        if best_idx is not None and best_length > 0:
            # Inherit the neighbour's tocatchment
            inherited = tocatchment.get(best_idx, UNRESOLVED_VAL)
            tocatchment[idx] = inherited
            hop_counts[idx]  = None
            resolved_spatial += 1
            status = 'resolved'
        else:
            status = 'no_shared_boundary'

        spatial_results.append({
            'index': idx,
            'featureid': to_pyint(row['featureid']),
            'neighbour_fid': best_fid,
            'shared_length': round(best_length, 4),
            'status': status
        })

    spatial_df = pd.DataFrame(spatial_results)
    spatial_df.to_csv(SPATIAL_CSV, index=False)

    spatial_status = spatial_df['status'].value_counts().to_dict()
    print(f"  Spatially resolved       : {resolved_spatial:,}")
    for k, v in spatial_status.items():
        print(f"    {k:<25} : {v:,}")
    print(f"  Spatial fallback log saved: {SPATIAL_CSV}")

else:
    print("  No gap catchments — spatial fallback skipped")

# ─────────────────────────────────────────────────────────────────────────────
# 8. APPLY RESULTS TO CATCHMENT DATAFRAME
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 8 — Applying results")

catchments['tocatchment'] = [float(tocatchment.get(i, UNRESOLVED_VAL)) for i in catchments.index]
catchments['hops']        = [float(hop_counts[i]) if hop_counts.get(i) is not None else float('nan')
                              for i in catchments.index]

# ─────────────────────────────────────────────────────────────────────────────
# 9. HOP SUMMARY & DIAGNOSTICS
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 9 — Summary")

total         = len(catchments)
terminals_out = (catchments['tocatchment'] == TERMINAL_VAL).sum()
unresolved    = (catchments['tocatchment'] == UNRESOLVED_VAL).sum()
routed        = total - terminals_out - unresolved

hop_dist = (
    catchments[catchments['hops'] >= 0]
    .groupby('hops').size()
    .rename('count').reset_index()
)
print("\nHop distribution (flowline-routed catchments):")
for _, row in hop_dist.iterrows():
    label = "direct" if row['hops'] == 0 else f"{int(row['hops'])} hop{'s' if row['hops'] > 1 else ''}"
    print(f"  {label:<12} : {row['count']:>8,}")

print(f"\n  {'terminals':<25} : {terminals_out:>8,}  (tocatchment=0)")
print(f"  {'unresolved/border gaps':<25} : {unresolved:>8,}  (tocatchment=-1)")
print(f"  {'routed':<25} : {routed:>8,}  (tocatchment>0)")
print(f"  {'total':<25} : {total:>8,}")

# Diagnostic sample of remaining unresolved
still_unresolved = catchments[catchments['tocatchment'] == UNRESOLVED_VAL]['featureid'].dropna()
if len(still_unresolved):
    print(f"\nDiagnostic — sample of remaining unresolved featureids ({len(still_unresolved):,} total):")
    for fid in list(still_unresolved)[:10]:
        fid_int = int(fid)
        in_r = fid_int in routing_dict
        in_t = fid_int in terminal_fids
        ds   = routing_dict.get(fid_int, 'NOT IN DICT')
        print(f"  featureid={fid_int} | in_routing={in_r} | in_terminal={in_t} | downstream={ds}")

# ─────────────────────────────────────────────────────────────────────────────
# 10. VALIDATE
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 10 — Validating")
dup_check = catchments.groupby('featureid')['tocatchment'].nunique()
multi = dup_check[dup_check > 1]
if len(multi):
    print(f"  WARNING: {len(multi)} FEATUREIDs map to multiple tocatchments")
else:
    print("  ✓ All FEATUREIDs map to a single tocatchment")

# ─────────────────────────────────────────────────────────────────────────────
# 11. SAVE TERMINAL CATCHMENTS
# ─────────────────────────────────────────────────────────────────────────────
terminal_mask   = catchments['tocatchment'] == TERMINAL_VAL
unresolved_mask = catchments['tocatchment'] == UNRESOLVED_VAL
terminal_cols   = [c for c in ['featureid', 'tocatchment', 'hops', 'reachcode']
                   if c in catchments.columns]
catchments[terminal_mask][terminal_cols].to_csv(TERMINAL_CSV, index=False)
print(f"\nTerminal catchments saved: {TERMINAL_CSV}")

# ─────────────────────────────────────────────────────────────────────────────
# 12. EXPORT
# ─────────────────────────────────────────────────────────────────────────────
print(f"\nSTEP 12 — Exporting to: {OUTPUT_GDB} | layer: {OUTPUT_FEATURE}")
export = catchments.copy()
export['featureid'] = export['featureid'].astype(float)
export.to_file(OUTPUT_GDB, layer=OUTPUT_FEATURE, driver="OpenFileGDB", engine='pyogrio')
print("  Done.")

print(f"""
══ Final Export Summary ═════════════════════════════════════
  tocatchment > 0  (routed)         : {routed:>8,}
  tocatchment == 0 (terminals)      : {terminals_out:>8,}
  tocatchment == -1 (border/gaps)   : {unresolved:>8,}
  total                             : {total:>8,}
═════════════════════════════════════════════════════════════
""")

# ─────────────────────────────────────────────────────────────────────────────
# 13. PLOT
# ─────────────────────────────────────────────────────────────────────────────
try:
    print("Plotting...")
    fig, ax = plt.subplots(1, 1, figsize=(12, 9))
    catchments.plot(ax=ax, linewidth=0, edgecolor='none', facecolor='steelblue', alpha=0.7)
    catchments[terminal_mask].plot(ax=ax, linewidth=0, edgecolor='none',
                                   facecolor='red', alpha=0.9,
                                   label=f'Terminals ({terminals_out:,})')
    catchments[unresolved_mask].plot(ax=ax, linewidth=0, edgecolor='none',
                                     facecolor='yellow', alpha=0.9,
                                     label=f'Unresolved / border ({unresolved:,})')
    ax.set_title(f'NHDPlusV2 Routed Catchments  ({total:,} catchments)', fontsize=11)
    ax.axis('off')
    ax.legend(loc='lower right', fontsize=8)
    plt.tight_layout()
    plot_path = str(Path(ROUTING_CSV).parent / 'routed_catchments.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Map saved: {plot_path}")
    plt.show()
except Exception as e:
    print(f"Plot skipped: {e}")