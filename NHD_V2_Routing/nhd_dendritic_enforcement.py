"""
NHD Dendritic Flow Path Enforcement  v3
========================================
Uses pynhd.prepare_nhdplus to enforce dendritic (single tocomid) flow paths,
then reinserts divergent flowlines (divergence == 2) with routing resolved
against the cleaned dendritic network via fromnode/tonode topology.

Exports:
  - comid -> tocomid routing CSV
  - terminal flowlines CSV
  - divergent reinsertion audit CSV
  - routed flowline layer to GDB
  - map PNG
"""

import geopandas as gpd
import pandas as pd
import pynhd as nhd
import matplotlib.pyplot as plt
from pathlib import Path
from shapely.geometry import MultiLineString

# ── Paths ─────────────────────────────────────────────────────────────────────

FLOWLINE_GDB      = r'E:\Basin_Project\NHD\NHD_all\NHDV2_MIHMS.gdb'
FLOWLINE_FEATURE  = 'Flowlines_clip'
OUTPUT_FEATURE    = 'Flowlines_Routed'
OUTPUT_GDB        = r'E:\Basin_Project\NHD\NHD_all\NHDV2_MIHMS.gdb'

VAA_PATH      = ''   # path to external VAA table — leave blank if embedded
OUTPUT_CSV    = r'C:\Users\CND367\Documents\Python_Scripts\hydrologic_indices\NHD_V2_Routing\comid.csv'
TERMINAL_CSV  = r'C:\Users\CND367\Documents\Python_Scripts\hydrologic_indices\NHD_V2_Routing\terminal_flowlines.csv'
DIVERGENT_CSV = r'C:\Users\CND367\Documents\Python_Scripts\hydrologic_indices\NHD_V2_Routing\divergent_reinserted.csv'

join_VAA = False   # set True + populate VAA_PATH if VAA is a separate table

# ── prepare_nhdplus settings ───────────────────────────────────────────────────
MIN_NETWORK_SIZE = 0    # km2  (0 = keep all)
MIN_PATH_LENGTH  = 0    # km   (0 = keep all)
MIN_PATH_SIZE    = 0    # km2  (0 = keep all)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def safe_int(val):
    """Convert a value to plain Python int, or None if null/unconvertible."""
    try:
        return None if pd.isna(val) else int(val)
    except (TypeError, ValueError):
        return None


def clean_vaa(df):
    """
    Cast VAA columns to the types expected by prepare_nhdplus.
    Works on a copy — does not mutate the caller's dataframe.
    """
    df = df.copy()

    flag_cols = ['terminalfl', 'startflag', 'divergence', 'streamorde', 'streamcalc']
    for col in flag_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    for col in ['fromnode', 'tonode']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # Ordering columns: MUST have unique non-zero values — never fill with 0
    # as that collapses all null rows into one group inside prepare_nhdplus.
    for col in ['hydroseq', 'levelpathi', 'terminalpa', 'pathlength']:
        if col in df.columns:
            s = pd.to_numeric(df[col], errors='coerce')
            null_mask = s.isna()
            if null_mask.any():
                max_val = int(s.max(skipna=True) or 0)
                s[null_mask] = max_val + 1 + df.index[null_mask]
                print(f'    {col}: filled {null_mask.sum():,} nulls with unique fallback values')
            df[col] = s.astype(int)

    for col in ['lengthkm', 'totdasqkm']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    return df


def build_fromnode_tocomid(df):
    """
    Build a fromnode -> comid lookup from a flowline dataframe.
    At confluences multiple reaches share a fromnode; we keep the first
    encountered (all are valid dendritic reaches so either is fine).
    Returns a plain-int-keyed dict.
    """
    lookup = {}
    for _, row in df[['comid', 'fromnode']].dropna().iterrows():
        fn = safe_int(row['fromnode'])
        cm = safe_int(row['comid'])
        if fn is not None and cm is not None and fn not in lookup:
            lookup[fn] = cm
    return lookup


def build_tocomid_from_nodes(df, fromnode_lookup):
    """
    Derive comid -> tocomid by mapping each row's tonode through
    fromnode_lookup (tonode of A == fromnode of B  =>  tocomid of A == comid of B).
    Returns a plain-int-keyed dict; value is int or None (terminal).
    """
    result = {}
    for _, row in df[['comid', 'tonode']].dropna().iterrows():
        cm = safe_int(row['comid'])
        tn = safe_int(row['tonode'])
        if cm is not None:
            result[cm] = fromnode_lookup.get(tn) if tn is not None else None
    return result


def resolve_divergent_tocomid(div_row, den_comids, den_fromnode_lookup,
                               orig_tocomid_dict, max_hops=20):
    """
    Find the correct tocomid for a divergent reach in the cleaned dendritic network.

    Strategy
    --------
    1. PRIMARY — topological: the divergent reach's tonode should match the
       fromnode of the next reach downstream.  If that reach survived in the
       dendritic network we're done.

    2. FALLBACK — graph walk: starting from the divergent reach's own comid,
       follow the original tocomid chain hop-by-hop until landing on a comid
       that exists in the dendritic network.

    Returns an int comid, or None if unresolvable.
    """
    # 1. Primary: tonode -> fromnode match in dendritic network
    tonode = safe_int(div_row.get('tonode'))
    if tonode is not None and tonode in den_fromnode_lookup:
        candidate = den_fromnode_lookup[tonode]
        if candidate in den_comids:
            return candidate

    # 2. Fallback: walk original graph downstream
    current = orig_tocomid_dict.get(safe_int(div_row.get('comid')))
    visited = set()
    for _ in range(max_hops):
        if current is None:
            return None
        if current in visited:
            return None          # cycle guard
        visited.add(current)
        if current in den_comids:
            return current
        current = orig_tocomid_dict.get(current)

    return None


# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1 — Loading flowlines")
print("=" * 60)
flowlines = gpd.read_file(FLOWLINE_GDB, layer=FLOWLINE_FEATURE)
flowlines.columns = flowlines.columns.str.lower()
print(f"  Loaded {len(flowlines):,} flowlines | CRS: {flowlines.crs}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. OPTIONAL VAA JOIN
# ─────────────────────────────────────────────────────────────────────────────
if join_VAA and VAA_PATH:
    print("\nSTEP 2 — Joining external VAA table...")
    vaa = gpd.read_file(VAA_PATH) if VAA_PATH.endswith('.shp') else pd.read_csv(VAA_PATH)
    vaa.columns = vaa.columns.str.lower()
    flowlines = flowlines.merge(vaa, on='comid', how='left', suffixes=('', '_vaa'))

# ─────────────────────────────────────────────────────────────────────────────
# 3. VERIFY REQUIRED COLUMNS
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 3 — Verifying required columns")
required = [
    'comid', 'lengthkm', 'ftype', 'terminalfl', 'fromnode', 'tonode',
    'totdasqkm', 'startflag', 'streamorde', 'streamcalc', 'terminalpa',
    'pathlength', 'divergence', 'hydroseq', 'levelpathi'
]
missing = [c for c in required if c not in flowlines.columns]
if missing:
    raise ValueError(
        f"Missing columns required by prepare_nhdplus: {missing}\n"
        "Ensure flowlines include NHDPlusV2 VAA attributes, or set join_VAA=True."
    )
print("  ✓ All required columns present")

n_total = len(flowlines)
print(f"\n  Pre-split divergence distribution:")
print(flowlines['divergence'].value_counts().sort_index().to_string())

# ─────────────────────────────────────────────────────────────────────────────
# 4. BUILD ORIGINAL GRAPH (before any filtering)
#    Used later for divergent fallback walks.
#    fromnode/tonode topology is the ground truth — do not rely on a tocomid
#    column that may be absent or stale in the GDB.
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 4 — Building original fromnode/tonode graph")

# Normalise node columns to int first
for col in ['comid', 'fromnode', 'tonode']:
    flowlines[col] = pd.to_numeric(flowlines[col], errors='coerce')

orig_fromnode_lookup  = build_fromnode_tocomid(flowlines)          # fromnode -> comid
orig_tocomid_dict     = build_tocomid_from_nodes(flowlines, orig_fromnode_lookup)  # comid -> tocomid

print(f"  Original fromnode lookup entries : {len(orig_fromnode_lookup):,}")
print(f"  Original tocomid dict entries    : {len(orig_tocomid_dict):,}")

# ─────────────────────────────────────────────────────────────────────────────
# 5. SEPARATE DIVERGENT REACHES BEFORE prepare_nhdplus
#    divergence == 2 : minor divergent path (gets purged by prepare_nhdplus)
#    divergence == 1 : main channel path
#    divergence == 0 : non-divergent
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 5 — Separating divergent reaches")

# Normalise divergence before splitting
flowlines['divergence'] = pd.to_numeric(flowlines['divergence'], errors='coerce').fillna(0).astype(int)

divergent_mask = flowlines['divergence'] == 2
divergent      = flowlines[divergent_mask].copy()
dendritic_in   = flowlines[~divergent_mask].copy()

print(f"  Divergent (div=2) set aside : {len(divergent):,}")
print(f"  Dendritic input             : {len(dendritic_in):,}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. CLEAN VAA COLUMNS
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 6 — Cleaning VAA columns for prepare_nhdplus")
dendritic_in = clean_vaa(dendritic_in)

# ─────────────────────────────────────────────────────────────────────────────
# 7. RUN prepare_nhdplus ON DENDRITIC SUBSET ONLY
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 7 — Running prepare_nhdplus (purge_non_dendritic=True)")
flowlines_den = nhd.prepare_nhdplus(
    dendritic_in,
    min_network_size=MIN_NETWORK_SIZE,
    min_path_length=MIN_PATH_LENGTH,
    min_path_size=MIN_PATH_SIZE,
    purge_non_dendritic=True,
    remove_isolated=False,
    terminal2nan=True,
)
print(f"  Remaining after prepare_nhdplus : {len(flowlines_den):,}")
print(f"  Removed by prepare_nhdplus      : {len(dendritic_in) - len(flowlines_den):,}")

# Validate
dup_check = flowlines_den.groupby('comid')['tocomid'].nunique()
multi = dup_check[dup_check > 1]
if len(multi):
    print(f"  WARNING: {len(multi)} COMIDs still have multiple tocomids")
else:
    print("  ✓ All COMIDs map to a single tocomid")

# ─────────────────────────────────────────────────────────────────────────────
# 8. REINSERT DIVERGENT REACHES WITH CORRECT ROUTING
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 8 — Reinserting divergent reaches with resolved routing")

# Dendritic network lookups — built from the CLEANED network
den_comids           = set(int(c) for c in flowlines_den['comid'])
den_fromnode_lookup  = build_fromnode_tocomid(flowlines_den)   # fromnode -> comid

print(f"  Dendritic comids             : {len(den_comids):,}")
print(f"  Dendritic fromnode entries   : {len(den_fromnode_lookup):,}")

# Clean divergent VAA (needed for correct int types)
divergent = clean_vaa(divergent)

# Resolve tocomid for each divergent reach
divergent['tocomid'] = [
    resolve_divergent_tocomid(
        row, den_comids, den_fromnode_lookup, orig_tocomid_dict
    )
    for row in divergent.to_dict('records')
]

n_div_resolved   = divergent['tocomid'].notna().sum()
n_div_unresolved = divergent['tocomid'].isna().sum()
print(f"  Divergent resolved to dendritic comid : {n_div_resolved:,}")
print(f"  Divergent unresolved (→ terminal)     : {n_div_unresolved:,}")

# Audit sample
print("\n  Sample divergent routing (first 10):")
audit_cols = [c for c in ['comid', 'tocomid', 'fromnode', 'tonode', 'divergence', 'ftype']
              if c in divergent.columns]
print(divergent[audit_cols].head(10).to_string())

# Save audit CSV
divergent[audit_cols].to_csv(DIVERGENT_CSV, index=False)
print(f"\n  Divergent audit saved: {DIVERGENT_CSV}")

# ─────────────────────────────────────────────────────────────────────────────
# 9. MERGE BACK INTO FINAL NETWORK
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 9 — Merging divergent reaches back into network")
flowlines_final = pd.concat([flowlines_den, divergent], ignore_index=True)
flowlines_final = gpd.GeoDataFrame(flowlines_final, geometry='geometry', crs=flowlines_den.crs)
print(f"  Final network size: {len(flowlines_final):,}")

# Confirm no COMID is duplicated (divergent comids should be unique)
dup_final = flowlines_final['comid'].duplicated().sum()
if dup_final:
    print(f"  WARNING: {dup_final:,} duplicate COMIDs in final network — check divergent/dendritic overlap")
else:
    print("  ✓ No duplicate COMIDs in final network")

# ─────────────────────────────────────────────────────────────────────────────
# 10. IDENTIFY TERMINAL FLOWLINES
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 10 — Identifying terminal flowlines")
terminal_mask = flowlines_final['tocomid'].isna()
terminal_cols = [c for c in ['comid', 'tocomid', 'streamorde', 'reachcode', 'totdasqkm']
                 if c in flowlines_final.columns]
terminals = flowlines_final[terminal_mask][terminal_cols].copy()
print(f"  Terminal flowlines (outlet / no downstream): {len(terminals):,}")
terminals.to_csv(TERMINAL_CSV, index=False)
print(f"  Saved: {TERMINAL_CSV}")

# ─────────────────────────────────────────────────────────────────────────────
# 11. BUILD comid -> tocomid ROUTING TABLE
# ─────────────────────────────────────────────────────────────────────────────
print("\nSTEP 11 — Building comid → tocomid routing table")
routing_cols  = ['comid', 'tocomid']
optional_cols = ['hydroseq', 'levelpathi', 'streamorde', 'totdasqkm', 'reachcode', 'divergence', 'ftype']
export_cols   = routing_cols + [c for c in optional_cols if c in flowlines_final.columns]
routing_table = flowlines_final[export_cols].copy()
routing_table.to_csv(OUTPUT_CSV, index=False)
print(f"  Saved: {OUTPUT_CSV}  ({len(routing_table):,} rows)")

# ─────────────────────────────────────────────────────────────────────────────
# 12. EXPORT ROUTED FLOWLINES TO GDB
# ─────────────────────────────────────────────────────────────────────────────
print(f"\nSTEP 12 — Exporting to: {OUTPUT_GDB} | layer: {OUTPUT_FEATURE}")
flowlines_final['geometry'] = [
    MultiLineString([feat]) if feat.geom_type == 'LineString' else feat
    for feat in flowlines_final.geometry
]
flowlines_final.to_file(OUTPUT_GDB, layer=OUTPUT_FEATURE, driver="OpenFileGDB", engine='pyogrio')
print("  Done.")

# ─────────────────────────────────────────────────────────────────────────────
# 13. SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
removed_by_prep = len(dendritic_in) - len(flowlines_den)
print(f"""
══ Summary ══════════════════════════════════════════════════
  Original flowlines
    total                       : {n_total:>10,}
    divergent (div=2) separated : {len(divergent):>10,}
    dendritic passed to prep    : {len(dendritic_in):>10,}

  prepare_nhdplus
    removed                     : {removed_by_prep:>10,}
    surviving dendritic reaches : {len(flowlines_den):>10,}

  Divergent reinsertion
    resolved to dendritic comid : {n_div_resolved:>10,}
    unresolved (set terminal)   : {n_div_unresolved:>10,}

  Final network
    total reaches               : {len(flowlines_final):>10,}
    terminal outlets            : {len(terminals):>10,}
═════════════════════════════════════════════════════════════
""")

# ─────────────────────────────────────────────────────────────────────────────
# 14. PLOT
# ─────────────────────────────────────────────────────────────────────────────
try:
    fig, ax = plt.subplots(1, 1, figsize=(12, 9))
    flowlines_den.plot(ax=ax, linewidth=0.4, color='steelblue', label='Dendritic')
    divergent[divergent['tocomid'].notna()].plot(
        ax=ax, linewidth=0.8, color='orange',
        label=f'Divergent reinserted ({n_div_resolved:,})')
    divergent[divergent['tocomid'].isna()].plot(
        ax=ax, linewidth=0.8, color='purple',
        label=f'Divergent unresolved ({n_div_unresolved:,})')
    flowlines_final[terminal_mask].plot(
        ax=ax, linewidth=1.2, color='red',
        label=f'Terminals ({len(terminals):,})')
    ax.set_title(
        f'NHDPlusV2 Network — Divergent Reinsertion  ({len(flowlines_final):,} reaches)',
        fontsize=11)
    ax.axis('off')
    ax.legend(loc='lower right', fontsize=8)
    plt.tight_layout()
    plot_path = str(Path(OUTPUT_CSV).parent / 'dendritic_network.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Map saved: {plot_path}")
    plt.show()
except Exception as e:
    print(f"Plot skipped: {e}")