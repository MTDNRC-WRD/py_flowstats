import numpy as np
import pandas as pd


def compute_pulse_stats(df, high_thresh=None, low_thresh=None):
    """
    Compute pulse counts and durations for high and low flow events.
    Uses 75th and 25th percentiles of daily flows by default.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing at least the column 'q' (daily streamflow values).
    high_thresh : float, optional
        High flow threshold. If None, defaults to the 75th percentile of flows.
    low_thresh : float, optional
        Low flow threshold. If None, defaults to the 25th percentile of flows.

    Returns
    -------
    dict
        Dictionary with the following keys:
        - 'high_pulse_count' : int
            Number of high flow pulses (flows >= high_thresh).
        - 'high_pulse_avg_dur' : float
            Mean duration (days) of high flow pulses.
        - 'low_pulse_count' : int
            Number of low flow pulses (flows <= low_thresh).
        - 'low_pulse_avg_dur' : float
            Mean duration (days) of low flow pulses.
        - 'high_thresh_used' : float
            Threshold applied for high flow pulses.
        - 'low_thresh_used' : float
            Threshold applied for low flow pulses.
    """
    flows = df["q"].values

    if high_thresh is None:
        high_thresh = np.percentile(flows, 75)
    if low_thresh is None:
        low_thresh = np.percentile(flows, 25)

    # Identify high and low events
    high_events = (flows >= high_thresh).astype(int)
    low_events = (flows <= low_thresh).astype(int)

    # Count event durations
    def event_durations(events):
        durations, count = [], 0
        for e in events:
            if e == 1:
                count += 1
            elif count > 0:
                durations.append(count)
                count = 0
        if count > 0:
            durations.append(count)
        return durations

    high_durations = event_durations(high_events)
    low_durations = event_durations(low_events)

    return {
        "high_pulse_count": len(high_durations),
        "high_pulse_avg_dur": np.mean(high_durations) if high_durations else 0,
        "low_pulse_count": len(low_durations),
        "low_pulse_avg_dur": np.mean(low_durations) if low_durations else 0,
        "high_thresh_used": high_thresh,
        "low_thresh_used": low_thresh,
    }


def compute_pulse_rate_stats(df, high_thresh, low_thresh):
    """
    Compute average rise/fall rates within high and low flow pulses,
    using thresholds from compute_pulse_stats (default: 75th / 25th percentiles).

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing at least the column 'q' (daily streamflow values).
    high_thresh : float
        Threshold for defining high flow pulses (typically 75th percentile).
    low_thresh : float
        Threshold for defining low flow pulses (typically 25th percentile).

    Returns
    -------
    dict
        Dictionary with the following keys:
        - 'high_pulse_rise_mean' : float or None
            Mean daily rise rate during high flow pulses.
        - 'high_pulse_fall_mean' : float or None
            Mean daily fall rate during high flow pulses.
        - 'low_pulse_rise_mean' : float or None
            Mean daily rise rate during low flow pulses.
        - 'low_pulse_fall_mean' : float or None
            Mean daily fall rate during low flow pulses.
    """
    flows = df["q"].values
    diffs = np.diff(flows)
    diffs = np.insert(diffs, 0, 0)  # align length

    # --- High flow pulses ---
    high_mask = flows >= high_thresh
    high_diffs = diffs[high_mask]
    high_rises = high_diffs[high_diffs > 0]
    high_falls = high_diffs[high_diffs < 0]

    # --- Low flow pulses ---
    low_mask = flows <= low_thresh
    low_diffs = diffs[low_mask]
    low_rises = low_diffs[low_diffs > 0]
    low_falls = low_diffs[low_diffs < 0]

    return {
        "high_pulse_rise_mean": np.mean(high_rises) if len(high_rises) else None,
        "high_pulse_fall_mean": np.mean(high_falls) if len(high_falls) else None,
        "low_pulse_rise_mean": np.mean(low_rises) if len(low_rises) else None,
        "low_pulse_fall_mean": np.mean(low_falls) if len(low_falls) else None,
    }


def _event_durations(events):
    """Helper to calculate consecutive event durations from a binary array."""
    durations, count = [], 0
    for e in events:
        if e == 1:
            count += 1
        elif count > 0:
            durations.append(count)
            count = 0
    if count > 0:
        durations.append(count)
    return durations
