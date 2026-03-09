"""Routes based on HUC12 and Ismainstem classification"""

import pandas as pd


CATCHMENTS_PARQUET = 'V2_Catchments.parquet'
HUC12_PARQUET = 'HUC12.parquet'

catchments = pd.read_parquet(CATCHMENTS_PARQUET)
huc12 = pd.read_parquet(HUC12_PARQUET)



def get_upstream_catchments(comid, catchments_df):
    """Traverse upstream from a given comid, returns list of all upstream comids."""
    upstream = []
    queue = [comid]
    visited = set()

    while queue:
        current = queue.pop()
        if current in visited:
            continue
        visited.add(current)

        tributaries = catchments_df[catchments_df['tocomid'] == current]['comid'].tolist()
        upstream.extend(tributaries)
        queue.extend(tributaries)

    return upstream


def get_upstream_hucs(huc12_id, huc12_df):
    """Traverse upstream HUC12s from a given HUC12, returns list of all upstream HUC12s."""
    upstream = []
    queue = [huc12_id]
    visited = set()

    while queue:
        current = queue.pop()
        if current in visited:
            continue
        visited.add(current)

        tributaries = huc12_df[huc12_df['tohuc'] == current]['huc12'].tolist()
        upstream.extend(tributaries)
        queue.extend(tributaries)

    return upstream


def route(comid, catchments_df, huc12_df):
    """
    For a given comid:
    - If ismainstem=1: find upstream catchments within the same HUC12,
      then find all upstream contributing HUC12s.
    - If ismainstem=0: find all upstream catchments only.
    """
    comid = int(comid)  # was str(comid)
    row = catchments_df[catchments_df['comid'] == comid]
    if row.empty:
        raise ValueError(f"COMID {comid} not found in catchments.")

    is_mainstem = row.iloc[0]['ismainstem']
    local_huc = row.iloc[0]['huc12']

    if is_mainstem == 1:  # was == '1'
        print(f"COMID {comid} is mainstem in HUC12 {local_huc}")

        all_upstream_comids = get_upstream_catchments(comid, catchments_df)
        local_upstream = catchments_df[
            (catchments_df['comid'].isin(all_upstream_comids)) &
            (catchments_df['huc12'] == local_huc)
        ]['comid'].tolist()

        print(f"  Upstream catchments in local HUC12: {local_upstream}")

        upstream_hucs = get_upstream_hucs(local_huc, huc12_df)
        print(f"  Upstream contributing HUC12s: {upstream_hucs}")

        return {
            'comid': comid,
            'is_mainstem': True,
            'local_huc12': local_huc,
            'upstream_catchments_in_huc': local_upstream,
            'upstream_hucs': upstream_hucs,
        }

    else:
        print(f"COMID {comid} is not mainstem")

        upstream_comids = get_upstream_catchments(comid, catchments_df)
        print(f"  Upstream catchments: {upstream_comids}")

        return {
            'comid': comid,
            'is_mainstem': False,
            'upstream_catchments': upstream_comids,
        }


if __name__ == "__main__":
    id_list = route(3853927, catchments, huc12)
    print(id_list)





