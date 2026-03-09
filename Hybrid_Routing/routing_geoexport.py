"""Routes based on HUC12 and Ismainstem classification"""

import pandas as pd
import geopandas as gpd


CATCHMENTS_PARQUET = 'V2_Catchments.parquet'
HUC12_PARQUET = 'HUC12.parquet'

catchments = gpd.read_parquet(CATCHMENTS_PARQUET)
huc12 = gpd.read_parquet(HUC12_PARQUET)


def get_upstream_catchments(comid, catchments_df):
    """
    Traverse upstream from a given comid and return all upstream comids.

    Inputs:
        comid        (int)           : The starting COMID to route upstream from.
        catchments_df (gpd.GeoDataFrame or pd.DataFrame) : Catchments table with columns:
                                        - comid (Int64)
                                        - tocomid (Int64)
                                        - huc12 (Int64)
                                        - ismainstem (Int64)

    Outputs:
        upstream (list of int) : List of all upstream COMIDs.
    """
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
    """
    Traverse upstream HUC12s from a given HUC12 and return all upstream HUC12s.

    Inputs:
        huc12_id (int)              : The starting HUC12 ID to route upstream from.
        huc12_df (gpd.GeoDataFrame) : HUC12 table with columns:
                                        - huc12 (Int64)
                                        - tohuc (Int64)
                                        - geometry (gpd.GeoSeries)

    Outputs:
        upstream (list of int) : List of all upstream HUC12 IDs.
    """
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


def export_huc12_geometries(local_huc, upstream_hucs, catchments_df, huc12_df):
    """
    Build a GeoDataFrame of HUC12 geometries for the full upstream network.
    The local (most downstream) HUC12 geometry is reconstructed by dissolving
    its constituent catchment polygons. Upstream HUC12 geometries are taken
    directly from the HUC12 layer.

    Inputs:
        local_huc     (int)              : HUC12 ID of the most downstream HUC12.
        upstream_hucs (list of int)      : List of upstream HUC12 IDs from get_upstream_hucs().
        catchments_df (gpd.GeoDataFrame) : Catchments table with geometry, used to dissolve
                                           the local HUC12 boundary. Must contain columns:
                                             - comid (Int64)
                                             - huc12 (Int64)
                                             - geometry (gpd.GeoSeries)
        huc12_df      (gpd.GeoDataFrame) : HUC12 table with columns:
                                             - huc12 (Int64)
                                             - tohuc (Int64)
                                             - geometry (gpd.GeoSeries)

    Outputs:
        result (gpd.GeoDataFrame) : GeoDataFrame with columns:
                                      - huc12 (Int64)
                                      - geometry (gpd.GeoSeries)
                                    One row per HUC12 (local + all upstream).
    """
    local_catchments = catchments_df[catchments_df['huc12'] == local_huc]
    if local_catchments.empty:
        print(f"  Warning: no catchments found for local HUC12 {local_huc}")
        local_geom = gpd.GeoDataFrame()
    else:
        local_geom = local_catchments.dissolve()
        local_geom = gpd.GeoDataFrame({'huc12': [local_huc], 'geometry': [local_geom.geometry.iloc[0]]})

    upstream_geom = huc12_df[huc12_df['huc12'].isin(upstream_hucs)][['huc12', 'geometry']]

    result = gpd.GeoDataFrame(pd.concat([local_geom, upstream_geom], ignore_index=True))
    result.crs = huc12_df.crs

    return result


def export_catchment_geometries(local_upstream, upstream_hucs, catchments_df):
    """
    Build a GeoDataFrame of all catchments within the routed upstream network.
    Includes catchments from all upstream HUC12s as well as the local upstream
    catchments identified within the downstream HUC12, deduplicated by COMID.

    Inputs:
        local_upstream (list of int)      : List of upstream COMIDs within the local HUC12,
                                            from get_upstream_catchments() filtered by HUC12.
        upstream_hucs  (list of int)      : List of upstream HUC12 IDs from get_upstream_hucs().
        catchments_df  (gpd.GeoDataFrame) : Catchments table with geometry. Must contain columns:
                                              - comid (Int64)
                                              - huc12 (Int64)
                                              - geometry (gpd.GeoSeries)

    Outputs:
        result (gpd.GeoDataFrame) : GeoDataFrame of all catchments with columns:
                                      - comid (Int64)
                                      - tocomid (Int64)
                                      - huc12 (Int64)
                                      - ismainstem (Int64)
                                      - geometry (gpd.GeoSeries)
                                    Deduplicated on comid.
    """
    hucs_catchments = catchments_df[catchments_df['huc12'].isin(upstream_hucs)]
    local_catchments = catchments_df[catchments_df['comid'].isin(local_upstream)]

    result = gpd.GeoDataFrame(
        pd.concat([hucs_catchments, local_catchments], ignore_index=True)
        .drop_duplicates(subset='comid')
    )

    return result


def route(comid, catchments_df, huc12_df,
          export_huc12_geom=False, export_catchment_geom=False):
    """
    Route upstream from a given COMID based on its mainstem classification.

    If ismainstem=1: finds all upstream catchments within the local HUC12,
                     then finds all upstream contributing HUC12s.
    If ismainstem=0: finds all upstream catchments regardless of HUC12 boundary.

    Inputs:
        comid                (int)                        : Target COMID to route from.
        catchments_df        (gpd.GeoDataFrame or pd.DataFrame) : Catchments table with columns:
                                                              - comid (Int64)
                                                              - tocomid (Int64)
                                                              - huc12 (Int64)
                                                              - ismainstem (Int64)
                                                              - geometry (gpd.GeoSeries, required if exporting)
        huc12_df             (gpd.GeoDataFrame)           : HUC12 table with columns:
                                                              - huc12 (Int64)
                                                              - tohuc (Int64)
                                                              - geometry (gpd.GeoSeries)
        export_huc12_geom    (bool, default False)        : If True, include a GeoDataFrame of
                                                            HUC12 geometries in the result.
                                                            Requires catchments_df to be a GeoDataFrame.
        export_catchment_geom (bool, default False)       : If True, include a GeoDataFrame of
                                                            catchment geometries in the result.
                                                            Requires catchments_df to be a GeoDataFrame.

    Outputs:
        result (dict) : Dictionary containing:
            Always present:
                - comid          (int)         : Input COMID.
                - is_mainstem    (bool)         : Whether the COMID is mainstem.

            If ismainstem=1:
                - local_huc12                  (int)         : HUC12 of the input COMID.
                - upstream_catchments_in_huc   (list of int) : Upstream COMIDs within local HUC12.
                - upstream_hucs                (list of int) : All upstream HUC12 IDs.
                - huc12_geometries             (gpd.GeoDataFrame, optional) : HUC12 geometries.
                - catchment_geometries         (gpd.GeoDataFrame, optional) : Catchment geometries.

            If ismainstem=0:
                - upstream_catchments          (list of int) : All upstream COMIDs.
                - catchment_geometries         (gpd.GeoDataFrame, optional) : Catchment geometries.
    """
    comid = int(comid)
    row = catchments_df[catchments_df['comid'] == comid]
    if row.empty:
        raise ValueError(f"COMID {comid} not found in catchments.")

    is_mainstem = row.iloc[0]['ismainstem']
    local_huc = row.iloc[0]['huc12']

    if is_mainstem == 1:
        print(f"COMID {comid} is mainstem in HUC12 {local_huc}")

        all_upstream_comids = get_upstream_catchments(comid, catchments_df)
        local_upstream = catchments_df[
            (catchments_df['comid'].isin(all_upstream_comids)) &
            (catchments_df['huc12'] == local_huc)
        ]['comid'].tolist()

        print(f"  Upstream catchments in local HUC12: {local_upstream}")

        upstream_hucs = get_upstream_hucs(local_huc, huc12_df)
        print(f"  Upstream contributing HUC12s: {upstream_hucs}")

        result = {
            'comid': comid,
            'is_mainstem': True,
            'local_huc12': local_huc,
            'upstream_catchments_in_huc': local_upstream,
            'upstream_hucs': upstream_hucs,
        }

        if export_huc12_geom:
            if not isinstance(catchments_df, gpd.GeoDataFrame):
                raise ValueError("catchments_df must be a GeoDataFrame to export geometries.")
            result['huc12_geometries'] = export_huc12_geometries(
                local_huc, upstream_hucs, catchments_df, huc12_df
            )
            print(f"  HUC12 geometries exported: {len(result['huc12_geometries'])} HUCs")

        if export_catchment_geom:
            if not isinstance(catchments_df, gpd.GeoDataFrame):
                raise ValueError("catchments_df must be a GeoDataFrame to export geometries.")
            result['catchment_geometries'] = export_catchment_geometries(
                local_upstream, upstream_hucs, catchments_df
            )
            print(f"  Catchment geometries exported: {len(result['catchment_geometries'])} catchments")

        return result

    else:
        print(f"COMID {comid} is not mainstem")

        upstream_comids = get_upstream_catchments(comid, catchments_df)
        print(f"  Upstream catchments: {upstream_comids}")

        result = {
            'comid': comid,
            'is_mainstem': False,
            'upstream_catchments': upstream_comids,
        }

        if export_catchment_geom:
            if not isinstance(catchments_df, gpd.GeoDataFrame):
                raise ValueError("catchments_df must be a GeoDataFrame to export geometries.")
            local_catchments = catchments_df[catchments_df['comid'].isin(upstream_comids)]
            result['catchment_geometries'] = gpd.GeoDataFrame(local_catchments)
            print(f"  Catchment geometries exported: {len(result['catchment_geometries'])} catchments")

        return result


if __name__ == "__main__":
    result = route(3853927, catchments, huc12,
                   export_huc12_geom=False,
                   export_catchment_geom=True)
    print(result)

    if 'huc12_geometries' in result:
        print(result['huc12_geometries'])
    if 'catchment_geometries' in result:
        print(result['catchment_geometries'])