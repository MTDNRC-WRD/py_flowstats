"""
NHD Dendritic Flow Path Enforcement
Cleans NHDPlusV2 flowlines to enforce dendritic (single tocomid) flow paths
and exports a comid -> tocomid lookup CSV.

tocomid is built from node topology AFTER divergence removal to ensure
the fromnode -> comid mapping is unambiguous.
"""

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import pynhd as nhd

# ── Paths ─────────────────────────────────────────────────────────────────────

FLOWLINE_GDB     = r'E:\Basin_Project\NHD\NHD_all\NHDV2_MIHMS.gdb'
FLOWLINE_FEATURE = 'Flowlines_clip'
OUTPUT_FEATURE   = 'Flowlines_Routed'
OUTPUT_GDB       = r'E:\Basin_Project\NHD\NHD_all\NHDV2_MIHMS.gdb'

VAA_PATH     = ''   # path to external VAA table if not embedded in flowlines
OUTPUT_CSV   = r'C:\Users\CND367\Documents\Python_Scripts\hydrologic_indices\NHD_routing\comid.csv'
TERMINAL_CSV = r'C:\Users\CND367\Documents\Python_Scripts\hydrologic_indices\NHD_routing\terminal_flowlines.csv'

join_VAA = False   # set True + populate VAA_PATH if VAA is a separate table

# ── 1. Load Data ──────────────────────────────────────────────────────────────
print("Loading flowlines...")
flowlines = gpd.read_file(FLOWLINE_GDB, layer=FLOWLINE_FEATURE)
flowlines.columns = flowlines.columns.str.lower()
print(f"  Loaded {len(flowlines):,} flowlines | CRS: {flowlines.crs}")

# ── 2. Optionally join external VAA table ─────────────────────────────────────
if join_VAA and VAA_PATH:
    print("Joining external VAA table...")
    vaa = gpd.read_file(VAA_PATH) if VAA_PATH.endswith('.shp') else pd.read_csv(VAA_PATH)
    vaa.columns = vaa.columns.str.lower()
    flowlines = flowlines.merge(vaa, on='comid', how='left', suffixes=('', '_vaa'))

# ── 3. Verify required columns ────────────────────────────────────────────────
required = ['comid', 'fromnode', 'tonode', 'divergence', 'streamorde', 'streamcalc', 'hydroseq']
missing = [c for c in required if c not in flowlines.columns]
if missing:
    raise ValueError(
        f"Missing required VAA columns: {missing}\n"
        "Ensure flowlines include NHDPlusV2 VAA attributes, or set join_VAA=True."
    )


















# # ── 4. Inspect divergence flags ───────────────────────────────────────────────
# # NHDPlusV2 divergence codes:
# #   0 = not divergent
# #   1 = main path of divergence (keep)
# #   2 = minor divergent path (remove)
# print("\nDivergence flag distribution:")
# print(flowlines['divergence'].value_counts().sort_index().to_string())
#
# n_total     = len(flowlines)
# n_divergent = (flowlines['divergence'] == 2).sum()
# print(f"\n  Total flowlines   : {n_total:,}")
# print(f"  Minor divergences : {n_divergent:,}  (divergence == 2)")
#
# # ── 5. Step 1 — Remove minor divergent paths (divergence == 2) ───────────────
# print("\nStep 1 – Removing minor divergent paths (divergence == 2)...")
# flowlines_den = flowlines[flowlines['divergence'] != 2].copy()
# print(f"  Remaining after step 1: {len(flowlines_den):,}")
#
# # ── 6. Step 2 — Resolve residual fromnode duplicates ─────────────────────────
# # After flag removal, rare data issues may still leave two reaches sharing a
# # fromnode. Keep the highest-priority (main channel) reach.
# print("Step 2 – Resolving residual fromnode duplicates...")
# flowlines_den['_priority'] = (
#     flowlines_den['streamcalc'].fillna(0) * 1000
#     + flowlines_den['streamorde'].fillna(0) * 100
#     - flowlines_den['hydroseq'].fillna(9e9) / 1e9   # lower hydroseq = preferred
# )
# before = len(flowlines_den)
# flowlines_den = (
#     flowlines_den
#     .sort_values('_priority', ascending=False)
#     .drop_duplicates(subset='fromnode', keep='first')
#     .copy()
# )
# flowlines_den.drop(columns=['_priority'], inplace=True)
# removed_step2 = before - len(flowlines_den)
# print(f"  Removed {removed_step2:,} residual duplicates | Remaining: {len(flowlines_den):,}")
#
# # ── 7. Build tocomid from node topology (AFTER cleaning) ─────────────────────
# # Build AFTER divergence removal so the fromnode -> comid mapping is
# # unambiguous — each fromnode now corresponds to exactly one comid.
# print("\nBuilding tocomid from node topology...")
# node_to_comid = flowlines_den.set_index("fromnode")["comid"].to_dict()
# flowlines_den["tocomid"] = flowlines_den["tonode"].map(node_to_comid)
#
# null_count = flowlines_den["tocomid"].isna().sum()
# total      = len(flowlines_den)
# print(f"  tocomid built: {total - null_count:,} routed | {null_count:,} terminals ({null_count/total:.1%})")
#
# # ── 8. Validate dendritic structure ──────────────────────────────────────────
# print("\nValidating dendritic structure...")
# dup_check = flowlines_den.groupby('comid')['tocomid'].nunique()
# multi = dup_check[dup_check > 1]
# if len(multi) > 0:
#     print(f"  WARNING: {len(multi)} COMIDs still have multiple tocomids – inspect manually.")
# else:
#     print("  ✓ All COMIDs map to a single tocomid.")
#
# # ── 9. Identify terminal flowlines ───────────────────────────────────────────
# terminal_mask = flowlines_den['tocomid'].isna()
# terminal_cols = ['comid', 'tocomid', 'streamorde', 'reachcode', 'totdasqkm']
# terminal_export_cols = [c for c in terminal_cols if c in flowlines_den.columns]
# terminals = flowlines_den[terminal_mask][terminal_export_cols].copy()
# print(f"\nTerminal flowlines (outlet / no downstream): {len(terminals):,}")
# terminals.to_csv(TERMINAL_CSV, index=False)
# print(f"  Saved: {TERMINAL_CSV}")
#
# # ── 10. Build comid -> tocomid routing table ──────────────────────────────────
# print("\nBuilding comid → tocomid routing table...")
# routing_cols   = ['comid', 'tocomid']
# optional_cols  = ['hydroseq', 'levelpathi', 'streamorde', 'totdasqkm', 'reachcode']
# export_cols    = routing_cols + [c for c in optional_cols if c in flowlines_den.columns]
# routing_table  = flowlines_den[export_cols].copy()
# routing_table.to_csv(OUTPUT_CSV, index=False)
# print(f"  Saved: {OUTPUT_CSV}  ({len(routing_table):,} rows)")
#
# # ── 11. Export cleaned flowlines ──────────────────────────────────────────────
# print(f"\nExporting cleaned flowlines to: {OUTPUT_GDB}")
# flowlines_den.to_file(OUTPUT_GDB, driver="OpenFileGDB", engine='pyogrio')
# print("  Done.")
#
# # ── 12. Summary ───────────────────────────────────────────────────────────────
# removed_total = n_total - len(flowlines_den)
# print(f"""
# ── Summary ──────────────────────────────────────────────────
#   Original flowlines       : {n_total:,}
#   Removed (divergence==2)  : {n_divergent:,}
#   Removed (residual dups)  : {removed_step2:,}
#   Final dendritic network  : {len(flowlines_den):,}
#   Terminal outlets         : {len(terminals):,}
# ─────────────────────────────────────────────────────────────
# """)
#
# # ── 13. Optional plot ─────────────────────────────────────────────────────────
# try:
#     fig, ax = plt.subplots(1, 1, figsize=(10, 8))
#
#     flowlines_den.plot(ax=ax, linewidth=0.4, color='steelblue')
#     flowlines_den[terminal_mask].plot(ax=ax, linewidth=1.2, color='red', label=f'Terminals ({len(terminals):,})')
#     ax.set_title(f'NHDPlusV2 Dendritic Network ({len(flowlines_den):,} reaches)', fontsize=11)
#     ax.axis('off')
#     ax.legend(loc='lower right', fontsize=8)
#
#     plt.tight_layout()
#     plot_path = str(Path(OUTPUT_CSV).parent / 'dendritic_network.png')
#     plt.savefig(plot_path, dpi=150, bbox_inches='tight')
#     print(f"Map saved: {plot_path}")
#     plt.show()
# except Exception as e:
#     print(f"Plot skipped: {e}")


# ── Enforce Dendritic Flow Paths ──────────────────────────────────────────────
print("Enforcing dendritic flow paths...")
flw_dendritic = nhd.prepare_nhdplus(
    flowlines,
    min_network_size=0,
    min_path_length=0,
    min_path_size=0,
    purge_non_dendritic=True,
    remove_isolated=False,
    terminal2nan=True
)

# ── Re-patch after prepare_nhdplus (it may re-null some) ─────────────────────
print("Re-patching any tocomids nulled by prepare_nhdplus...")
null_before = flw_dendritic["tocomid"].isna().sum()

node_to_comid2 = flw_dendritic.drop_duplicates(subset="fromnode").set_index("fromnode")["comid"].to_dict()
valid_comids   = set(flw_dendritic["comid"])
mask           = flw_dendritic["tocomid"].isna()
candidate      = flw_dendritic.loc[mask, "tonode"].map(node_to_comid2)
flw_dendritic.loc[mask, "tocomid"] = candidate.where(candidate.isin(valid_comids))

recovered  = null_before - flw_dendritic["tocomid"].isna().sum()
null_count = flw_dendritic["tocomid"].isna().sum()
total      = len(flw_dendritic)
print(f"  Recovered {recovered} additional tocomids after prepare_nhdplus")
print(f"  Final null tocomid: {null_count} of {total} ({null_count/total:.1%}) — genuine terminals")

# # ── Topological Sort ──────────────────────────────────────────────────────────
# print("Sorting topologically...")
# sorted_flw = nhd.topoogical_sort(
#     flw_dendritic,
#     id_col="comid",
#     toid_col="tocomid"
# )

# ── Verification ──────────────────────────────────────────────────────────────
dupes = flw_dendritic.groupby("comid")["tocomid"].nunique()
assert (dupes <= 1).all(), "Still has branching flow paths!"
print("All flowlines are dendritic ✓")

# ── Diagnostic: inspect remaining terminals ───────────────────────────────────
terminals = flw_dendritic[flw_dendritic["tocomid"].isna()]
diag_cols = [c for c in ["comid", "divergence", "streamcalc", "hydroseq", "streamorde", "terminalfl"]
             if c in terminals.columns]

# ── Export terminal flowlines CSV ─────────────────────────────────────────────
terminals[diag_cols].to_csv(TERMINAL_CSV, index=False)
print(f"Terminal flowlines saved: {TERMINAL_CSV}")

# ── Export CSV ────────────────────────────────────────────────────────────────
print("\nExporting comid -> tocomid lookup CSV...")
lookup = flw_dendritic[["comid", "tocomid"]].copy()
lookup.to_csv(OUTPUT_CSV, index=False)
print(f"Saved: {OUTPUT_CSV}")

# ── Export GDB ────────────────────────────────────────────────────────────────

flw_dendritic.to_file(
        FLOWLINE_GDB,
        layer=OUTPUT_FEATURE,
        driver="OpenFileGDB",
        engine='pyogrio',
        geometry_type="LineString"
    )

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 10))

flw_dendritic.plot(ax=ax, color="steelblue", linewidth=0.5, label="Flowlines")

flw_dendritic[flw_dendritic["tocomid"].isna()].plot(
    ax=ax, color="red", linewidth=1.5, label="Terminal outlets (null tocomid)"
)

ax.set_title(
    f"NHDPlus Dendritic Flowlines — Terminal Outlets Highlighted\n"
    f"({null_count} terminals of {total} total flowlines)"
)
ax.legend()
plt.tight_layout()
plt.show()